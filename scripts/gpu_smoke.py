import torch


def main() -> None:
    assert torch.cuda.is_available(), "CUDA not available — check driver / cu128 wheel"
    dev = torch.device("cuda")
    name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    a = torch.randn(1024, 1024, device=dev)
    b = torch.randn(1024, 1024, device=dev)
    c = (a @ b).sum().item()
    print(f"OK device={name} capability=sm_{cap[0]}{cap[1]} torch={torch.__version__} matmul={c:.1f}")


if __name__ == "__main__":
    main()
