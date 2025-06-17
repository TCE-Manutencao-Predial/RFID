#!/bin/bash

source ./scripts/config.sh

cd $ROOT_BACKEND

sudo setenforce 0
make run
sudo setenforce 1
