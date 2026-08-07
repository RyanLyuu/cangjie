FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    git \
    wget \
    curl \
    zip \
    unzip \
    rsync \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"; \
    elif [ "$arch" = "aarch64" ]; then \
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"; \
    else \
    echo "Unsupported architecture: $arch"; \
    exit 1; \
    fi && \
    wget $MINICONDA_URL -O miniconda.sh && \
    mkdir -p /root/.conda && \
    bash miniconda.sh -b -p /root/miniconda3 && \
    rm -f miniconda.sh

ENV PATH="/root/miniconda3/bin:${PATH}"

RUN pip3 install --upgrade pip

WORKDIR /home

RUN wget https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz
RUN tar xzvf apache-maven-3.9.9-bin.tar.gz
ENV PATH="/home/apache-maven-3.9.9/bin:${PATH}"
RUN rm apache-maven-3.9.9-bin.tar.gz

RUN git clone https://github.com/hx062312/x2cangjie.git /home/x2cangjie

WORKDIR /home/x2cangjie

SHELL ["/bin/bash", "-c"]

RUN conda init bash

RUN echo "source /root/.bashrc && conda activate x2cangjie" > /etc/profile.d/conda.sh && \
    echo "conda activate x2cangjie" >> ~/.bashrc

RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

RUN conda env create -f environment.yaml

RUN curl -s "https://get.sdkman.io" | bash && \
    bash -c "source /root/.sdkman/bin/sdkman-init.sh && \
        sdk install java 8.0.432-kona && \
        sdk install java 11.0.26-tem && \
        sdk install java 21.0.3-graal && \
        sdk default java 8.0.432-kona"

RUN mkdir -p /home/x2cangjie/misc/sitter-libs
RUN git clone https://github.com/tree-sitter/tree-sitter-java.git /home/x2cangjie/misc/sitter-libs/java
RUN git clone https://github.com/tree-sitter/tree-sitter-python.git /home/x2cangjie/misc/sitter-libs/python

RUN mkdir -p /home/x2cangjie/misc/java-callgraph
RUN git clone https://github.com/gousiosg/java-callgraph.git /home/x2cangjie/misc/java-callgraph
WORKDIR /home/x2cangjie/misc/java-callgraph
RUN source "$HOME/.sdkman/bin/sdkman-init.sh" && mvn clean install -DskipTests

WORKDIR /home/x2cangjie

RUN git clone --depth 1 --branch v1.1.0 https://gitcode.com/Cangjie/CangjieCorpus.git /home/x2cangjie/misc/CangjieCorpus

RUN wget https://github.com/github/codeql-action/releases/download/codeql-bundle-v2.20.0/codeql-bundle-linux64.tar.gz
RUN tar -xvf codeql-bundle-linux64.tar.gz -C /home/x2cangjie/misc
RUN rm codeql-bundle-linux64.tar.gz
ENV PATH="/home/x2cangjie/misc/codeql:$PATH"

RUN git clone https://github.com/github/vscode-codeql-starter.git
WORKDIR /home/x2cangjie/vscode-codeql-starter
RUN git submodule update --init --remote
WORKDIR /home/x2cangjie/vscode-codeql-starter/ql
RUN git checkout 3b2e55bc2ac942ac2cf2646f5c69acd081ce8ea2

WORKDIR /home/x2cangjie
RUN cp misc/sitter-libs/java/queries/* vscode-codeql-starter/codeql-custom-queries-java 2>/dev/null || true
