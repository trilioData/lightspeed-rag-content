ARG EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
ARG FLAVOR=cpu
ARG HERMETIC=false

FROM registry.access.redhat.com/ubi9/python-312 as cpu-base
ARG EMBEDDING_MODEL
ARG FLAVOR

FROM registry.redhat.io/rhai/base-image-cuda-12.9-rhel9:3.3 as gpu-base
ARG EMBEDDING_MODEL
ARG FLAVOR
USER 0
RUN dnf install -y python3.12 python3.12-pip libcudnn9 libnccl libcusparselt0

FROM ${FLAVOR}-base as lightspeed-rag-builder
ARG EMBEDDING_MODEL
ARG FLAVOR
ARG HERMETIC

USER 0
WORKDIR /workdir

COPY requirements.gpu.txt .
RUN pip3.12 install --no-cache-dir -r requirements.gpu.txt && ln -s /usr/local/lib/python3.12/site-packages/llama_index/core/_static/nltk_cache /root/nltk_data

COPY tvk-content ./tvk-content
# TODO: Add runbooks for MVP2
# COPY runbooks ./runbooks

COPY embeddings_model ./embeddings_model
RUN cd embeddings_model; if [ "$HERMETIC" == "true" ]; then \
        cp /cachi2/output/deps/generic/model.safetensors model.safetensors; \
    else \
        curl -L -O https://huggingface.co/sentence-transformers/all-mpnet-base-v2/resolve/9a3225965996d404b775526de6dbfe85d3368642/model.safetensors; \
    fi

RUN if [ "$FLAVOR" == "gpu" ]; then \
        python3.12 -c "import torch; print(torch.version.cuda); print(torch.cuda.is_available());"; \
    fi

COPY scripts/generate_embeddings.py .
RUN set -e && python3.12 generate_embeddings.py -f tvk-content -md embeddings_model \
            -mn ${EMBEDDING_MODEL} -o vector_db \
            -i tvk_rag_index -hb $HERMETIC
# TODO: Add runbooks for MVP2
# RUN set -e && python3.12 generate_embeddings.py -f tvk-content -r runbooks/alerts -md embeddings_model \
#             -mn ${EMBEDDING_MODEL} -o vector_db \
#             -i tvk_rag_index -hb $HERMETIC

FROM registry.access.redhat.com/ubi9/ubi-minimal@sha256:12db9874bd753eb98b1ab3d840e75de5d6842ac0604fbd68c012adefe97140be
COPY --from=lightspeed-rag-builder /workdir/vector_db /rag/vector_db
COPY --from=lightspeed-rag-builder /workdir/embeddings_model /rag/embeddings_model

# this directory is checked by ecosystem-cert-preflight-checks task in Konflux
RUN mkdir /licenses
COPY LICENSE /licenses/

LABEL name="tvk-lightspeed-rag-content"
LABEL maintainer=Trilio\ Data\ Inc.
LABEL vendor=Trilio\ Data\ Inc.
LABEL version=5.4.1
LABEL release=RC
LABEL summary="OpenShift Lightspeed RAG content for TVK"
LABEL description="TrilioVault RAG content for OpenShift Lightspeed"


USER 65532:65532
