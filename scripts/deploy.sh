#!/bin/bash

# Atenção:
# Este Script deve ser executado na raiz do projeto
# Ou pela makefile através do "make deploy"


# Parâmetros de Deploy
# ----------------------------

source ./scripts/config.sh


# Atualizar projeto do git
# ----------------------------

atualizar_projeto_local() {
    echo "[Deploy] Verificando atualizações do projeto no repositório git..."
    git pull
    echo "[Deploy] Atualizações do repositório git concluídas."
}



# Deploy Frontend
# ----------------------------

deploy_frontend() {
    echo "[Deploy] Iniciando instalação do Frontend..."
    
    if [ -e $ROOT_FRONTEND ]; then
        echo "[Deploy] Diretório do Frontend existente encontrado. Removendo arquivos antigos..."
        sudo rm -rv $ROOT_FRONTEND
    fi

    echo "[Deploy] Criando diretório do Frontend..."
    sudo mkdir -pv $ROOT_FRONTEND

    echo "[Deploy] Copiando arquivos HTML e estáticos para o diretório do Frontend..."
    sudo cp -v "app/templates/index.html" $ROOT_FRONTEND"/index.html"
    sudo cp -vr "app/static" $ROOT_FRONTEND

    if [ -e $HTACCESS_FILE ]; then
        echo "[Deploy] Encontrado arquivo .htaccess. Instalando no Frontend..."
        sudo cp -v $HTACCESS_FILE $ROOT_FRONTEND"/.htaccess"
        echo "[Deploy] Arquivo .htaccess instalado com sucesso."
    else
        echo "[Deploy] Arquivo .htaccess não encontrado. Pulando esta etapa."
    fi

    echo "[Deploy] Instalação do Frontend concluída."
}



# Deploy Backend
# ---------------------

deploy_backend() {
    echo "[Deploy] Iniciando instalação do Backend..."
    
    if [ -e $ROOT_BACKEND ]; then
        echo "[Deploy] Projeto antigo do Backend encontrado. Atualizando arquivos..."
        dir_atual=$(pwd)
        cd $ROOT_BACKEND
        git restore .
        git pull
        cd $dir_atual
        echo "[Deploy] Atualização do Backend concluída."
    else
        echo "[Deploy] Diretório do Backend não encontrado. Criando novo repositório..."
        sudo mkdir -pv $ROOT_SOFTWARES
        git clone $GIT_REPO_LINK
        sudo mv -v $GIT_REPO_NAME $ROOT_BACKEND
        echo "[Deploy] Repositório do Backend clonado para: $ROOT_BACKEND"
    fi

    echo "[Deploy] Ajustando permissões do diretório do Backend..."
    sudo chown -Rv $(whoami) $ROOT_BACKEND
    echo "[Deploy] Permissões do Backend ajustadas."

    if [ -e $ROOT_BACKEND/*.log ]; then
        echo "[Deploy] Ajustando permissões dos arquivos de log..."
        sudo chown -v tcego:tcego $ROOT_BACKEND/*.log
        echo "[Deploy] Permissões dos arquivos de log ajustadas."
    fi

    echo "[Deploy] Configurando projeto do Backend..."
    dir_atual=$(pwd)
    cd $ROOT_BACKEND
    make setup
    cd $dir_atual
    echo "[Deploy] Configuração do Backend concluída."

    echo "[Deploy] Verificando permissões de execução para scripts do Backend..."
    [ ! -x "$ROOT_BACKEND/scripts/deploy.sh" ] && sudo chmod -v +x "$ROOT_BACKEND/scripts/deploy.sh"
    [ ! -x "$ROOT_BACKEND/scripts/run.sh" ] && sudo chmod -v +x "$ROOT_BACKEND/scripts/run.sh"

    CURRENT_CONTEXT=$(ls -Z "$ROOT_BACKEND/scripts/run.sh" | awk -F: '{print $3}')
    if [[ "$CURRENT_CONTEXT" != "bin_t" ]]; then
        echo "[Deploy] Ajustando contexto SELinux para o script run.sh..."
        sudo chcon -t bin_t "$ROOT_BACKEND/scripts/run.sh"
        echo "[Deploy] Contexto SELinux ajustado."
    else
        echo "[Deploy] Contexto SELinux já configurado corretamente."
    fi

    echo "[Deploy] Instalação do Backend concluída."
}


# Deploy Configuração do Apache
# ------------------------------------

deploy_apache() {
    echo "[Deploy] Iniciando configuração do Apache..."
    
    if [ -e "./scripts/$APACHE_CONFIG_FILE" ]; then
        echo "[Deploy] Arquivo de configuração do Apache encontrado. Copiando para o diretório..."
        sudo cp -v "./scripts/$APACHE_CONFIG_FILE" "$APACHE_CONFIG_DIR/$APACHE_CONFIG"
        echo "[Deploy] Configuração do Apache concluída."
    else
        echo "[Deploy] Arquivo de configuração do Apache não encontrado. Pulando esta etapa."
    fi
}


# Deploy Servico
# ------------------------------------

deploy_servico() {
    echo "[Deploy] Iniciando instalação do serviço..."

    if [ -e "/usr/lib/systemd/system/$SERVICE_NAME" ]; then
        echo "[Deploy] Serviço existente encontrado. Removendo configuração antiga..."
        sudo rm -v "/usr/lib/systemd/system/$SERVICE_NAME"
    fi

    echo "[Deploy] Copiando novo arquivo de serviço..."
    sudo cp -v scripts/$SERVICE_NAME /usr/lib/systemd/system/$SERVICE_NAME

    if ! systemctl is-enabled "$SERVICE_NAME" && [ $AUTO_HABILITAR_SERVICO ]; then
        echo "[Deploy] Serviço desabilitado. Habilitando..."
        sudo systemctl enable "$SERVICE_NAME"
        echo "[Deploy] Serviço habilitado."
    else
        echo "[Deploy] Serviço já habilitado."
    fi

    echo "[Deploy] Reiniciando o serviço..."
    make service-reload
    make service-restart
    echo "[Deploy] Serviço reiniciado com sucesso."
}


# Main
# -------------------------------------

main() {
    echo "[Deploy] Iniciando processo de Deploy..."
    atualizar_projeto_local
    deploy_frontend
    deploy_backend
    deploy_apache
    deploy_servico
    echo "[Deploy] Processo de Deploy concluído com sucesso!"
}

main
