#!/bin/sh
# `uv sync` of the `ml` group for a machine with no GPU, shared by the worker image and the Space.
# The lock resolves torch with its CUDA packages on Linux (several GB); everything else comes from
# the lock, and torch is then installed at the locked version from PyTorch's CPU-only index. The
# arguments go to `uv sync` (for instance --no-install-project). Run from the folder of uv.lock.
set -eu

skip=""
for package in torch triton cuda-bindings cuda-pathfinder cuda-toolkit \
  nvidia-cublas nvidia-cuda-cupti nvidia-cuda-nvrtc nvidia-cuda-runtime nvidia-cudnn-cu13 \
  nvidia-cufft nvidia-cufile nvidia-curand nvidia-cusolver nvidia-cusparse \
  nvidia-cusparselt-cu13 nvidia-nccl-cu13 nvidia-nvjitlink nvidia-nvshmem-cu13 nvidia-nvtx; do
  skip="$skip --no-install-package $package"
done

# --inexact: a second sync (with the project) must not remove the torch installed below.
# shellcheck disable=SC2086  # $skip is a list of flags
uv sync --locked --no-default-groups --group ml --inexact $skip "$@"
version=$(sed -n '/^name = "torch"$/{n;s/version = "\(.*\)"/\1/p;}' uv.lock)
uv pip install --no-deps "torch==${version}" --index-url https://download.pytorch.org/whl/cpu
