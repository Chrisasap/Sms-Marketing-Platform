#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
#  ██████╗ ██╗      █████╗ ███████╗████████╗██╗    ██╗ █████╗ ██╗   ██╗███████╗
#  ██╔══██╗██║     ██╔══██╗██╔════╝╚══██╔══╝██║    ██║██╔══██╗██║   ██║██╔════╝
#  ██████╔╝██║     ███████║███████╗   ██║   ██║ █╗ ██║███████║██║   ██║█████╗
#  ██╔══██╗██║     ██╔══██║╚════██║   ██║   ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝
#  ██████╔╝███████╗██║  ██║███████║   ██║   ╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗
#  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝    ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝ ╚══════╝
#                  SMS Marketing Platform - Installer
# ============================================================================

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# -- Colors & Formatting -----------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'
CHECK="${GREEN}✔${RESET}"
CROSS="${RED}✘${RESET}"
ARROW="${CYAN}➜${RESET}"
WARN="${YELLOW}⚠${RESET}"
BOLT="${MAGENTA}⚡${RESET}"

# -- Helpers ------------------------------------------------------------------
banner() {
    echo ""
    echo -e "${MAGENTA}${BOLD}"
    cat << 'ART'
    ____  __           __  _       __
   / __ )/ /___ ______/ /_| |     / /___ __   _____
  / __  / / __ `/ ___/ __/| | /| / / __ `/ | / / _ \
 / /_/ / / /_/ (__  ) /__ | |/ |/ / /_/ /| |/ /  __/
/_____/_/\__,_/____/\__/ |__/|__/\__,_/ |___/\___/

         ███████╗███╗   ███╗███████╗
         ██╔════╝████╗ ████║██╔════╝
         ███████╗██╔████╔██║███████╗
         ╚════██║██║╚██╔╝██║╚════██║
         ███████║██║ ╚═╝ ██║███████║
         ╚══════╝╚═╝     ╚═╝╚══════╝
ART
    echo -e "${RESET}"
    echo -e "  ${DIM}Multi-Tenant SMS/MMS Marketing Platform${RESET}"
    echo -e "  ${DIM}Installer v${VERSION}${RESET}"
    echo ""
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
}

info()    { echo -e "  ${ARROW} ${WHITE}$1${RESET}"; }
success() { echo -e "  ${CHECK} ${GREEN}$1${RESET}"; }
warn()    { echo -e "  ${WARN} ${YELLOW}$1${RESET}"; }
fail()    { echo -e "  ${CROSS} ${RED}$1${RESET}"; }
header()  { echo ""; echo -e "  ${BOLT} ${BOLD}${CYAN}$1${RESET}"; echo -e "  ${DIM}$(printf '%.0s─' {1..45})${RESET}"; }

spinner() {
    local pid=$1
    local msg=$2
    local spin='⣾⣽⣻⢿⡿⣟⣯⣷'
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  ${MAGENTA}${spin:i++%${#spin}:1}${RESET} ${DIM}${msg}${RESET}"
        sleep 0.1
    done
    printf "\r"
}

prompt_yn() {
    local msg=$1
    local default=${2:-y}
    local yn
    if [[ "$default" == "y" ]]; then
        echo -ne "  ${ARROW} ${WHITE}${msg}${RESET} ${DIM}[Y/n]${RESET} "
    else
        echo -ne "  ${ARROW} ${WHITE}${msg}${RESET} ${DIM}[y/N]${RESET} "
    fi
    read -r yn
    yn=${yn:-$default}
    [[ "$yn" =~ ^[Yy] ]]
}

prompt_input() {
    local msg=$1
    local default=${2:-}
    local result
    if [[ -n "$default" ]]; then
        echo -ne "  ${ARROW} ${WHITE}${msg}${RESET} ${DIM}[${default}]${RESET}: "
    else
        echo -ne "  ${ARROW} ${WHITE}${msg}${RESET}: "
    fi
    read -r result
    echo "${result:-$default}"
}

prompt_secret() {
    local msg=$1
    local result
    echo -ne "  ${ARROW} ${WHITE}${msg}${RESET}: "
    read -rs result
    echo ""
    echo "$result"
}

check_command() {
    command -v "$1" &>/dev/null
}

require_command() {
    if ! check_command "$1"; then
        fail "$1 is not installed"
        return 1
    fi
    success "$1 found: $(command -v "$1")"
    return 0
}

get_docker_compose_cmd() {
    if docker compose version &>/dev/null 2>&1; then
        echo "docker compose"
    elif check_command docker-compose; then
        echo "docker-compose"
    else
        echo ""
    fi
}

# -- Prerequisite checks -----------------------------------------------------
check_prerequisites() {
    header "CHECKING PREREQUISITES"

    local missing=0

    # Docker
    if check_command docker; then
        local docker_ver
        docker_ver=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
        success "Docker ${docker_ver:-installed}"
    else
        fail "Docker not found — install from https://docs.docker.com/get-docker/"
        missing=1
    fi

    # Docker Compose
    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd)
    if [[ -n "$compose_cmd" ]]; then
        success "Docker Compose found ($compose_cmd)"
    else
        fail "Docker Compose not found"
        missing=1
    fi

    # Git
    if check_command git; then
        success "Git $(git --version | awk '{print $3}')"
    else
        fail "Git not found"
        missing=1
    fi

    # Docker daemon
    if docker info &>/dev/null 2>&1; then
        success "Docker daemon is running"
    else
        fail "Docker daemon is not running — start Docker Desktop or dockerd"
        missing=1
    fi

    # Optional: local dev tools
    echo ""
    info "${DIM}Optional (for local development without Docker):${RESET}"

    if check_command python3; then
        success "Python $(python3 --version 2>&1 | awk '{print $2}') ${DIM}(optional)${RESET}"
    elif check_command python; then
        success "Python $(python --version 2>&1 | awk '{print $2}') ${DIM}(optional)${RESET}"
    else
        warn "Python not found (needed only for local dev)"
    fi

    if check_command node; then
        success "Node.js $(node --version) ${DIM}(optional)${RESET}"
    else
        warn "Node.js not found (needed only for local dev)"
    fi

    if [[ $missing -eq 1 ]]; then
        echo ""
        fail "Missing required dependencies. Install them and re-run this script."
        exit 1
    fi
}

# -- Environment setup -------------------------------------------------------
generate_secret() {
    if check_command openssl; then
        openssl rand -hex 32
    elif check_command python3; then
        python3 -c "import secrets; print(secrets.token_hex(32))"
    else
        head -c 64 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 64
    fi
}

setup_environment() {
    header "ENVIRONMENT CONFIGURATION"

    local env_file="${SCRIPT_DIR}/backend/.env"

    if [[ -f "$env_file" ]]; then
        warn "backend/.env already exists"
        if ! prompt_yn "Overwrite existing .env file?" "n"; then
            success "Keeping existing .env"
            return 0
        fi
    fi

    echo ""
    info "Let's configure your environment. Press Enter to accept defaults."
    echo ""

    # -- Generate secrets
    local jwt_secret
    jwt_secret=$(generate_secret)

    # -- Database
    echo -e "  ${BOLD}${WHITE}Database${RESET}"
    local db_user db_pass db_name db_host db_port
    db_user=$(prompt_input "PostgreSQL user" "blastwave")
    db_pass=$(prompt_input "PostgreSQL password" "blastwave")
    db_name=$(prompt_input "Database name" "blastwave")
    db_host=$(prompt_input "Database host" "db")
    db_port=$(prompt_input "Database port" "5432")
    echo ""

    # -- Redis
    echo -e "  ${BOLD}${WHITE}Redis${RESET}"
    local redis_host redis_port
    redis_host=$(prompt_input "Redis host" "redis")
    redis_port=$(prompt_input "Redis port" "6379")
    echo ""

    # -- Bandwidth (SMS Provider)
    echo -e "  ${BOLD}${WHITE}Bandwidth SMS Provider${RESET} ${DIM}(leave blank to skip)${RESET}"
    local bw_account bw_token bw_secret bw_app_id
    bw_account=$(prompt_input "Bandwidth Account ID" "")
    bw_token=$(prompt_input "Bandwidth API Token" "")
    bw_secret=$(prompt_input "Bandwidth API Secret" "")
    bw_app_id=$(prompt_input "Bandwidth Application ID" "")
    echo ""

    # -- Stripe
    echo -e "  ${BOLD}${WHITE}Stripe Billing${RESET} ${DIM}(leave blank to skip)${RESET}"
    local stripe_sk stripe_pk stripe_wh stripe_p1 stripe_p2 stripe_p3
    stripe_sk=$(prompt_input "Stripe Secret Key" "")
    stripe_pk=$(prompt_input "Stripe Publishable Key" "")
    stripe_wh=$(prompt_input "Stripe Webhook Secret" "")
    stripe_p1=$(prompt_input "Stripe Price ID (Starter)" "")
    stripe_p2=$(prompt_input "Stripe Price ID (Growth)" "")
    stripe_p3=$(prompt_input "Stripe Price ID (Enterprise)" "")
    echo ""

    # -- AI
    echo -e "  ${BOLD}${WHITE}AI Providers${RESET} ${DIM}(leave blank to skip)${RESET}"
    local openai_key anthropic_key
    openai_key=$(prompt_input "OpenAI API Key" "")
    anthropic_key=$(prompt_input "Anthropic API Key" "")
    echo ""

    # -- S3
    echo -e "  ${BOLD}${WHITE}S3 / Object Storage${RESET} ${DIM}(leave blank to skip)${RESET}"
    local s3_bucket s3_endpoint aws_key aws_secret
    s3_bucket=$(prompt_input "S3 Bucket" "blastwave-media")
    s3_endpoint=$(prompt_input "S3 Endpoint URL" "")
    aws_key=$(prompt_input "AWS Access Key ID" "")
    aws_secret=$(prompt_input "AWS Secret Access Key" "")
    echo ""

    # -- Write .env file
    cat > "$env_file" << ENVEOF
# ============================================================================
# BlastWave SMS - Environment Configuration
# Generated by install.sh on $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================================

# -- App ----------------------------------------------------------------------
APP_URL=http://localhost:5173
WEBHOOK_BASE_URL=http://localhost:8000
DEBUG=true

# -- Database -----------------------------------------------------------------
DATABASE_URL=postgresql+asyncpg://${db_user}:${db_pass}@${db_host}:${db_port}/${db_name}
DATABASE_URL_SYNC=postgresql://${db_user}:${db_pass}@${db_host}:${db_port}/${db_name}
POSTGRES_USER=${db_user}
POSTGRES_PASSWORD=${db_pass}
POSTGRES_DB=${db_name}

# -- Redis --------------------------------------------------------------------
REDIS_URL=redis://${redis_host}:${redis_port}/0

# -- JWT Authentication -------------------------------------------------------
JWT_SECRET=${jwt_secret}
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# -- Bandwidth SMS Provider ---------------------------------------------------
BANDWIDTH_ACCOUNT_ID=${bw_account}
BANDWIDTH_API_TOKEN=${bw_token}
BANDWIDTH_API_SECRET=${bw_secret}
BANDWIDTH_APPLICATION_ID=${bw_app_id}

# -- Stripe Billing -----------------------------------------------------------
STRIPE_SECRET_KEY=${stripe_sk}
STRIPE_PUBLISHABLE_KEY=${stripe_pk}
STRIPE_WEBHOOK_SECRET=${stripe_wh}
STRIPE_PRICE_STARTER=${stripe_p1}
STRIPE_PRICE_GROWTH=${stripe_p2}
STRIPE_PRICE_ENTERPRISE=${stripe_p3}

# -- AI Providers -------------------------------------------------------------
OPENAI_API_KEY=${openai_key}
ANTHROPIC_API_KEY=${anthropic_key}

# -- S3 / Object Storage ------------------------------------------------------
S3_BUCKET=${s3_bucket}
S3_ENDPOINT_URL=${s3_endpoint}
AWS_ACCESS_KEY_ID=${aws_key}
AWS_SECRET_ACCESS_KEY=${aws_secret}
ENVEOF

    success "Environment file created: backend/.env"
}

# -- Quick setup (just defaults) ----------------------------------------------
setup_environment_quick() {
    header "QUICK ENVIRONMENT SETUP"

    local env_file="${SCRIPT_DIR}/backend/.env"

    if [[ -f "$env_file" ]]; then
        success "backend/.env already exists — keeping it"
        return 0
    fi

    local jwt_secret
    jwt_secret=$(generate_secret)

    cat > "$env_file" << ENVEOF
# ============================================================================
# BlastWave SMS - Environment Configuration (Quick Setup Defaults)
# Generated by install.sh on $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================================

# -- App ----------------------------------------------------------------------
APP_URL=http://localhost:5173
WEBHOOK_BASE_URL=http://localhost:8000
DEBUG=true

# -- Database -----------------------------------------------------------------
DATABASE_URL=postgresql+asyncpg://blastwave:blastwave@db:5432/blastwave
DATABASE_URL_SYNC=postgresql://blastwave:blastwave@db:5432/blastwave
POSTGRES_USER=blastwave
POSTGRES_PASSWORD=blastwave
POSTGRES_DB=blastwave

# -- Redis --------------------------------------------------------------------
REDIS_URL=redis://redis:6379/0

# -- JWT Authentication -------------------------------------------------------
JWT_SECRET=${jwt_secret}
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# -- Bandwidth SMS Provider (configure later) ---------------------------------
BANDWIDTH_ACCOUNT_ID=
BANDWIDTH_API_TOKEN=
BANDWIDTH_API_SECRET=
BANDWIDTH_APPLICATION_ID=

# -- Stripe Billing (configure later) ----------------------------------------
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_STARTER=
STRIPE_PRICE_GROWTH=
STRIPE_PRICE_ENTERPRISE=

# -- AI Providers (configure later) -------------------------------------------
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# -- S3 / Object Storage (configure later) ------------------------------------
S3_BUCKET=blastwave-media
S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
ENVEOF

    success "Default .env created (edit backend/.env to add API keys later)"
}

# -- Docker build & launch ---------------------------------------------------
docker_build() {
    header "BUILDING DOCKER IMAGES"

    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd)

    info "Building all services (this may take a few minutes)..."
    echo ""

    if $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" build 2>&1 | while IFS= read -r line; do
        # Show build progress with cleaner output
        if [[ "$line" =~ ^"#"[0-9]+ ]]; then
            printf "\r  ${DIM}  %s${RESET}" "$(echo "$line" | head -c 70)"
        fi
    done; then
        echo ""
        success "All Docker images built successfully"
    else
        echo ""
        fail "Docker build failed — check output above"
        exit 1
    fi
}

docker_up() {
    header "LAUNCHING SERVICES"

    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd)

    info "Starting PostgreSQL and Redis..."
    $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" up -d db redis 2>/dev/null

    # Wait for databases
    info "Waiting for databases to be healthy..."
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" exec -T db pg_isready -U blastwave &>/dev/null; then
            break
        fi
        retries=$((retries - 1))
        sleep 1
    done

    if [[ $retries -eq 0 ]]; then
        fail "PostgreSQL did not become ready in time"
        exit 1
    fi
    success "PostgreSQL is ready"

    retries=15
    while [[ $retries -gt 0 ]]; do
        if $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" exec -T redis redis-cli ping &>/dev/null; then
            break
        fi
        retries=$((retries - 1))
        sleep 1
    done
    success "Redis is ready"

    # Run migrations
    info "Running database migrations..."
    if $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" run --rm migrate 2>/dev/null; then
        success "Database migrations complete"
    else
        warn "Migration failed — may need manual intervention"
    fi

    # Start all services
    info "Starting all application services..."
    $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" up -d api worker beat frontend 2>/dev/null

    # Wait for API to be ready
    info "Waiting for API to come online..."
    retries=30
    while [[ $retries -gt 0 ]]; do
        if curl -sf http://localhost:8000/health &>/dev/null; then
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done

    if [[ $retries -gt 0 ]]; then
        success "API is online"
    else
        warn "API health check timed out (may still be starting)"
    fi

    success "Frontend is available at http://localhost:5173"
}

# -- Local development setup --------------------------------------------------
local_setup_backend() {
    header "BACKEND SETUP (Local)"

    local py_cmd="python3"
    check_command python3 || py_cmd="python"

    if ! check_command "$py_cmd"; then
        fail "Python not found — install Python 3.12+"
        exit 1
    fi

    cd "${SCRIPT_DIR}/backend"

    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        info "Creating Python virtual environment..."
        $py_cmd -m venv venv
        success "Virtual environment created"
    else
        success "Virtual environment exists"
    fi

    # Activate and install
    info "Installing Python dependencies..."
    if [[ -f "venv/Scripts/activate" ]]; then
        # Windows / Git Bash
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi

    pip install --upgrade pip -q 2>/dev/null
    pip install -r requirements.txt -q 2>/dev/null
    success "Python dependencies installed"

    # Fix .env for local dev (localhost instead of docker hostnames)
    if [[ -f .env ]] && grep -q "@db:" .env; then
        info "Updating .env for local development..."
        sed -i.bak 's/@db:/@localhost:/g; s/@redis:/@localhost:/g' .env
        rm -f .env.bak
        success ".env updated for localhost connections"
    fi

    cd "${SCRIPT_DIR}"
}

local_setup_frontend() {
    header "FRONTEND SETUP (Local)"

    if ! check_command node; then
        fail "Node.js not found — install Node.js 20+"
        exit 1
    fi

    cd "${SCRIPT_DIR}/frontend"

    info "Installing npm dependencies..."
    npm install --silent 2>/dev/null
    success "Frontend dependencies installed"

    cd "${SCRIPT_DIR}"
}

# -- Status -------------------------------------------------------------------
show_status() {
    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd)

    header "SERVICE STATUS"
    echo ""
    $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || \
    $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" ps 2>/dev/null
    echo ""
}

# -- Finish -------------------------------------------------------------------
show_complete() {
    echo ""
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    echo -e "  ${GREEN}${BOLD}INSTALLATION COMPLETE${RESET} ${BOLT}"
    echo ""
    echo -e "  ${WHITE}${BOLD}Access Points:${RESET}"
    echo -e "    ${ARROW} Frontend     ${CYAN}http://localhost:5173${RESET}"
    echo -e "    ${ARROW} API          ${CYAN}http://localhost:8000${RESET}"
    echo -e "    ${ARROW} API Docs     ${CYAN}http://localhost:8000/docs${RESET}"
    echo -e "    ${ARROW} Health Check ${CYAN}http://localhost:8000/health${RESET}"
    echo ""
    echo -e "  ${WHITE}${BOLD}Useful Commands:${RESET}"

    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd)

    echo -e "    ${DIM}# View logs${RESET}"
    echo -e "    ${WHITE}${compose_cmd} logs -f api${RESET}"
    echo ""
    echo -e "    ${DIM}# Stop everything${RESET}"
    echo -e "    ${WHITE}${compose_cmd} down${RESET}"
    echo ""
    echo -e "    ${DIM}# Restart${RESET}"
    echo -e "    ${WHITE}${compose_cmd} up -d${RESET}"
    echo ""
    echo -e "    ${DIM}# Run migrations${RESET}"
    echo -e "    ${WHITE}${compose_cmd} run --rm migrate${RESET}"
    echo ""
    echo -e "    ${DIM}# Run backend tests${RESET}"
    echo -e "    ${WHITE}${compose_cmd} exec api pytest${RESET}"
    echo ""
    echo -e "    ${DIM}# View this menu again${RESET}"
    echo -e "    ${WHITE}./install.sh --status${RESET}"
    echo ""
    echo -e "  ${WHITE}${BOLD}Next Steps:${RESET}"
    echo -e "    1. Register an account at ${CYAN}http://localhost:5173/register${RESET}"
    echo -e "    2. Add your Bandwidth API keys in ${DIM}backend/.env${RESET}"
    echo -e "    3. Add your Stripe keys for billing in ${DIM}backend/.env${RESET}"
    echo ""
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
}

# -- Uninstall / Clean --------------------------------------------------------
do_clean() {
    header "CLEANING UP"

    local compose_cmd
    compose_cmd=$(get_docker_compose_cmd)

    if [[ -n "$compose_cmd" ]]; then
        if prompt_yn "Stop and remove all containers?" "y"; then
            $compose_cmd -f "${SCRIPT_DIR}/docker-compose.yml" down -v --remove-orphans 2>/dev/null || true
            success "Containers and volumes removed"
        fi
    fi

    if prompt_yn "Remove Python virtual environment?" "n"; then
        rm -rf "${SCRIPT_DIR}/backend/venv"
        success "Virtual environment removed"
    fi

    if prompt_yn "Remove node_modules?" "n"; then
        rm -rf "${SCRIPT_DIR}/frontend/node_modules"
        success "node_modules removed"
    fi

    if prompt_yn "Remove backend/.env?" "n"; then
        rm -f "${SCRIPT_DIR}/backend/.env"
        success ".env removed"
    fi

    success "Cleanup complete"
}

# -- Help ---------------------------------------------------------------------
show_help() {
    banner
    echo -e "  ${WHITE}${BOLD}Usage:${RESET}  ./install.sh [option]"
    echo ""
    echo -e "  ${WHITE}${BOLD}Options:${RESET}"
    echo -e "    ${CYAN}(none)${RESET}       Interactive guided setup"
    echo -e "    ${CYAN}--quick${RESET}      Quick setup with defaults (Docker)"
    echo -e "    ${CYAN}--local${RESET}      Set up for local development (no Docker app)"
    echo -e "    ${CYAN}--status${RESET}     Show running service status"
    echo -e "    ${CYAN}--clean${RESET}      Tear down and clean up everything"
    echo -e "    ${CYAN}--help${RESET}       Show this help message"
    echo ""
    echo -e "  ${WHITE}${BOLD}Examples:${RESET}"
    echo -e "    ${DIM}# Full interactive install${RESET}"
    echo -e "    ./install.sh"
    echo ""
    echo -e "    ${DIM}# Quick install with all defaults (fastest)${RESET}"
    echo -e "    ./install.sh --quick"
    echo ""
    echo -e "    ${DIM}# Local dev (Python venv + npm install, bring your own DB)${RESET}"
    echo -e "    ./install.sh --local"
    echo ""
}

# -- Main installation modes --------------------------------------------------
install_docker_interactive() {
    check_prerequisites
    setup_environment
    docker_build
    docker_up
    show_status
    show_complete
}

install_docker_quick() {
    check_prerequisites
    setup_environment_quick
    docker_build
    docker_up
    show_status
    show_complete
}

install_local() {
    header "LOCAL DEVELOPMENT SETUP"
    info "This sets up the backend & frontend for local development."
    info "You'll need PostgreSQL and Redis running separately."
    echo ""

    # Check for Python and Node
    local has_py=0 has_node=0
    check_command python3 && has_py=1
    check_command python && has_py=1
    check_command node && has_node=1

    if [[ $has_py -eq 0 ]]; then
        fail "Python 3 is required for local backend development"
        exit 1
    fi
    if [[ $has_node -eq 0 ]]; then
        fail "Node.js is required for local frontend development"
        exit 1
    fi

    # Environment
    setup_environment

    # Fix env for local
    local env_file="${SCRIPT_DIR}/backend/.env"
    if [[ -f "$env_file" ]]; then
        sed -i.bak 's/@db:/@localhost:/g; s/@redis:/@localhost:/g' "$env_file"
        rm -f "${env_file}.bak"
    fi

    local_setup_backend
    local_setup_frontend

    echo ""
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    echo -e "  ${GREEN}${BOLD}LOCAL SETUP COMPLETE${RESET} ${BOLT}"
    echo ""
    echo -e "  ${WHITE}${BOLD}Start development:${RESET}"
    echo ""
    echo -e "    ${DIM}# Terminal 1 — Start PostgreSQL & Redis with Docker${RESET}"
    echo -e "    ${WHITE}docker compose up -d db redis${RESET}"
    echo ""
    echo -e "    ${DIM}# Terminal 2 — Run database migrations${RESET}"
    echo -e "    ${WHITE}cd backend && source venv/bin/activate${RESET}"
    echo -e "    ${WHITE}alembic upgrade head${RESET}"
    echo ""
    echo -e "    ${DIM}# Terminal 2 — Start API server${RESET}"
    echo -e "    ${WHITE}uvicorn app.main:app --reload --port 8000${RESET}"
    echo ""
    echo -e "    ${DIM}# Terminal 3 — Start Celery worker${RESET}"
    echo -e "    ${WHITE}cd backend && source venv/bin/activate${RESET}"
    echo -e "    ${WHITE}celery -A app.celery_app worker -l info${RESET}"
    echo ""
    echo -e "    ${DIM}# Terminal 4 — Start frontend${RESET}"
    echo -e "    ${WHITE}cd frontend && npm run dev${RESET}"
    echo ""
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
}

install_interactive() {
    echo ""
    echo -e "  ${WHITE}${BOLD}Choose installation mode:${RESET}"
    echo ""
    echo -e "    ${CYAN}1)${RESET} ${WHITE}Docker${RESET} ${DIM}— Full stack in containers (recommended)${RESET}"
    echo -e "    ${CYAN}2)${RESET} ${WHITE}Docker Quick${RESET} ${DIM}— Defaults, no prompts, just go${RESET}"
    echo -e "    ${CYAN}3)${RESET} ${WHITE}Local Dev${RESET} ${DIM}— Python venv + npm, bring your own DB${RESET}"
    echo ""
    echo -ne "  ${ARROW} ${WHITE}Select [1-3]${RESET}: "
    read -r choice

    case "$choice" in
        1) install_docker_interactive ;;
        2) install_docker_quick ;;
        3) install_local ;;
        *) warn "Invalid choice"; exit 1 ;;
    esac
}

# -- Entry point --------------------------------------------------------------
main() {
    banner

    case "${1:-}" in
        --quick)    install_docker_quick ;;
        --local)    install_local ;;
        --status)   show_status ;;
        --clean)    do_clean ;;
        --help|-h)  show_help ;;
        "")         install_interactive ;;
        *)          warn "Unknown option: $1"; show_help; exit 1 ;;
    esac
}

main "$@"
