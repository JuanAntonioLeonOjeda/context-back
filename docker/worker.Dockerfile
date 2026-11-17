# The `worker` service: the jobs that need the `ml` group (the own classifier and the sentence
# encoder of the stories), which never go into the API image (ADR-0016). It runs worker.sh: classify
# the new articles with the own model, then bring the stories and their trees up to date.
FROM python:3.13-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/opt/hf

WORKDIR /app

# The lock resolves torch with its CUDA packages on Linux (several GB) for a machine with no GPU.
# Everything else comes from the lock; torch is then installed, at the locked version, from the
# CPU-only index of PyTorch.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-default-groups --group ml --no-install-project \
      --no-install-package torch --no-install-package triton \
      --no-install-package cuda-bindings --no-install-package cuda-pathfinder \
      --no-install-package cuda-toolkit \
      --no-install-package nvidia-cublas --no-install-package nvidia-cuda-cupti \
      --no-install-package nvidia-cuda-nvrtc --no-install-package nvidia-cuda-runtime \
      --no-install-package nvidia-cudnn-cu13 --no-install-package nvidia-cufft \
      --no-install-package nvidia-cufile --no-install-package nvidia-curand \
      --no-install-package nvidia-cusolver --no-install-package nvidia-cusparse \
      --no-install-package nvidia-cusparselt-cu13 --no-install-package nvidia-nccl-cu13 \
      --no-install-package nvidia-nvjitlink --no-install-package nvidia-nvshmem-cu13 \
      --no-install-package nvidia-nvtx \
 && version=$(sed -n '/^name = "torch"$/{n;s/version = "\(.*\)"/\1/p;}' uv.lock) \
 && uv pip install --no-deps "torch==${version}" --index-url https://download.pytorch.org/whl/cpu

# The stories' encoder in the image, so a run never reaches the Hub (on 2026-11-16 that check hung
# for a day) and every deploy has the same weights.
ARG ENCODER=sentence-transformers/paraphrase-multilingual-mpnet-base-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${ENCODER}')"
ENV HF_HUB_OFFLINE=1

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY data ./data
COPY --chmod=755 docker/worker.sh /usr/local/bin/worker.sh
RUN uv sync --locked --no-default-groups --group ml --inexact \
      --no-install-package torch --no-install-package triton \
      --no-install-package cuda-bindings --no-install-package cuda-pathfinder \
      --no-install-package cuda-toolkit \
      --no-install-package nvidia-cublas --no-install-package nvidia-cuda-cupti \
      --no-install-package nvidia-cuda-nvrtc --no-install-package nvidia-cuda-runtime \
      --no-install-package nvidia-cudnn-cu13 --no-install-package nvidia-cufft \
      --no-install-package nvidia-cufile --no-install-package nvidia-curand \
      --no-install-package nvidia-cusolver --no-install-package nvidia-cusparse \
      --no-install-package nvidia-cusparselt-cu13 --no-install-package nvidia-nccl-cu13 \
      --no-install-package nvidia-nvjitlink --no-install-package nvidia-nvshmem-cu13 \
      --no-install-package nvidia-nvtx

RUN useradd --system --no-create-home --uid 10001 app && chmod -R a+rX /opt/hf
USER app

ENTRYPOINT ["worker.sh"]
