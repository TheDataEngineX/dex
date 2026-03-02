#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# DEX — System Dependencies Installer
# ---------------------------------------------------------------------------
# Installs all Linux system-level packages required to develop, test,
# and run the DEX project on a local machine.
#
# Usage:
#   uv run poe setup-system          # via poe task (recommended)
#   bash scripts/setup-system.sh     # direct execution
#
# Supports: Ubuntu/Debian, Fedora/RHEL, Arch Linux, macOS (Homebrew)
# ---------------------------------------------------------------------------

set -euo pipefail

# ── Colour helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

# ── Detect OS / package manager ────────────────────────────────────────────
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif command -v apt-get &>/dev/null; then
        OS="debian"
    elif command -v dnf &>/dev/null; then
        OS="fedora"
    elif command -v pacman &>/dev/null; then
        OS="arch"
    else
        fail "Unsupported OS. Install the packages listed below manually."
        echo ""
        echo "Required packages:"
        echo "  - git, curl, build tools (gcc, make)"
        echo "  - Python 3.11+"
        echo "  - Java 17+ JRE (for PySpark)"
        echo "  - Docker + Docker Compose (for full stack)"
        echo ""
        echo "Optional packages:"
        echo "  - Trivy (security scanning)"
        echo "  - Terraform (infrastructure provisioning)"
        echo "  - actionlint (GitHub Actions linting)"
        exit 1
    fi
}

# ── Package lists per OS ───────────────────────────────────────────────────
# Core: minimum required to develop and run tests
# Optional: needed only for specific workflows

install_debian() {
    info "Updating apt package index..."
    sudo apt-get update -qq

    info "Installing core system packages..."
    sudo apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        build-essential \
        libffi-dev \
        libssl-dev \
        openjdk-17-jre-headless

    info "Installing Docker (if not present)..."
    if ! command -v docker &>/dev/null; then
        sudo apt-get install -y --no-install-recommends \
            docker.io \
            docker-compose-plugin
        sudo usermod -aG docker "$USER" 2>/dev/null || true
        warn "Added $USER to docker group — log out and back in to take effect"
    else
        ok "Docker already installed"
    fi
}

install_fedora() {
    info "Installing core system packages..."
    sudo dnf install -y \
        git \
        curl \
        gcc \
        gcc-c++ \
        make \
        libffi-devel \
        openssl-devel \
        java-17-openjdk-headless

    if ! command -v docker &>/dev/null; then
        info "Installing Docker..."
        sudo dnf install -y docker docker-compose-plugin
        sudo systemctl enable --now docker
        sudo usermod -aG docker "$USER" 2>/dev/null || true
        warn "Added $USER to docker group — log out and back in to take effect"
    else
        ok "Docker already installed"
    fi
}

install_arch() {
    info "Installing core system packages..."
    sudo pacman -Syu --noconfirm \
        git \
        curl \
        base-devel \
        openssl \
        jre17-openjdk-headless

    if ! command -v docker &>/dev/null; then
        info "Installing Docker..."
        sudo pacman -S --noconfirm docker docker-compose
        sudo systemctl enable --now docker
        sudo usermod -aG docker "$USER" 2>/dev/null || true
        warn "Added $USER to docker group — log out and back in to take effect"
    else
        ok "Docker already installed"
    fi
}

install_macos() {
    if ! command -v brew &>/dev/null; then
        fail "Homebrew not found. Install from https://brew.sh"
        exit 1
    fi

    info "Installing core packages via Homebrew..."
    brew install git curl openjdk@17

    # Symlink Java so JAVA_HOME works
    if [[ -d "/opt/homebrew/opt/openjdk@17" ]]; then
        sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk \
            /Library/Java/JavaVirtualMachines/openjdk-17.jdk 2>/dev/null || true
    fi

    if ! command -v docker &>/dev/null; then
        info "Installing Docker Desktop..."
        brew install --cask docker
        warn "Open Docker Desktop to complete setup"
    else
        ok "Docker already installed"
    fi
}

# ── Install uv (if not present) ───────────────────────────────────────────
install_uv() {
    if command -v uv &>/dev/null; then
        ok "uv already installed ($(uv --version))"
    else
        info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ok "uv installed"
    fi
}

# ── Optional tools ─────────────────────────────────────────────────────────
install_optional() {
    echo ""
    info "Installing optional development tools..."

    # Trivy — security scanner
    if ! command -v trivy &>/dev/null; then
        info "Installing Trivy..."
        case "$OS" in
            debian)
                sudo apt-get install -y --no-install-recommends wget apt-transport-https gnupg
                wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo gpg --dearmor -o /usr/share/keyrings/trivy.gpg 2>/dev/null
                echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | sudo tee /etc/apt/sources.list.d/trivy.list > /dev/null
                sudo apt-get update -qq && sudo apt-get install -y trivy
                ;;
            fedora)  sudo dnf install -y trivy 2>/dev/null || warn "Trivy not in default repos — install manually from https://trivy.dev" ;;
            arch)    sudo pacman -S --noconfirm trivy 2>/dev/null || warn "Install trivy from AUR" ;;
            macos)   brew install trivy ;;
        esac
    else
        ok "Trivy already installed"
    fi

    # actionlint — GitHub Actions linter
    if ! command -v actionlint &>/dev/null; then
        info "Installing actionlint..."
        case "$OS" in
            macos)  brew install actionlint ;;
            *)      go install github.com/rhysd/actionlint/cmd/actionlint@latest 2>/dev/null || warn "actionlint: install Go first or use Docker fallback (poe actionlint)" ;;
        esac
    else
        ok "actionlint already installed"
    fi
}

# ── Verification ───────────────────────────────────────────────────────────
verify() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    info "Verifying installation..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    local status=0

    # Required
    for cmd in git curl python3 java uv docker; do
        if command -v "$cmd" &>/dev/null; then
            ver=$("$cmd" --version 2>&1 | head -1)
            ok "$cmd — $ver"
        else
            if [[ "$cmd" == "docker" ]]; then
                warn "$cmd — not found (optional for full stack)"
            else
                fail "$cmd — NOT FOUND"
                status=1
            fi
        fi
    done

    # Java version check
    if command -v java &>/dev/null; then
        java_ver=$(java -version 2>&1 | head -1)
        ok "Java runtime — $java_ver"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [[ $status -eq 0 ]]; then
        echo ""
        ok "All system dependencies installed!"
        echo ""
        info "Next steps:"
        echo "  1. uv run poe setup          # Install Python deps + pre-commit hooks"
        echo "  2. uv run poe check-all      # Verify everything works"
        echo "  3. uv run poe dev            # Start dev server"
        echo ""
    else
        echo ""
        fail "Some dependencies are missing — see above"
        exit 1
    fi
}

# ── Main ───────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║         DEX — System Dependencies Installer                    ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    detect_os
    info "Detected OS: $OS"
    echo ""

    case "$OS" in
        debian) install_debian ;;
        fedora) install_fedora ;;
        arch)   install_arch ;;
        macos)  install_macos ;;
    esac

    install_uv
    install_optional
    verify
}

main "$@"
