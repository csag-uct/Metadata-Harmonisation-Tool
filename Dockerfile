FROM mambaorg/micromamba:1.5.1

USER root

COPY --chown=$MAMBA_USER:$MAMBA_USER . .

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN micromamba install --yes --file env_docker.yml && micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1  # (otherwise python will not be found)

RUN echo "source activate env" > ~/.bashrc

WORKDIR app/

RUN mkdir input/ && chown -R $MAMBA_USER:$MAMBA_USER input/

RUN mkdir results/ && chown -R $MAMBA_USER:$MAMBA_USER results/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]