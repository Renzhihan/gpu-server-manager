#!/usr/bin/env python3
"""
GPU 负载测试工具
用于测试任务监控系统，可以占满指定的GPU显卡
"""

import argparse
import time
import sys

try:
    import torch
except ImportError:
    print("错误：需要安装 PyTorch")
    print("安装命令：pip install torch")
    sys.exit(1)


def get_gpu_info():
    """获取GPU信息"""
    if not torch.cuda.is_available():
        print("错误：未检测到CUDA GPU")
        sys.exit(1)

    gpu_count = torch.cuda.device_count()
    print(f"\n检测到 {gpu_count} 个GPU:")
    for i in range(gpu_count):
        props = torch.cuda.get_device_properties(i)
        total_mem = props.total_memory / (1024**3)  # GB
        print(f"  GPU {i}: {props.name} ({total_mem:.2f} GB)")
    print()
    return gpu_count


def occupy_gpu(gpu_id, memory_ratio=0.9, duration=None, matrix_size=10000):
    """
    占用指定GPU

    参数:
        gpu_id: GPU ID (0, 1, 2...)
        memory_ratio: 显存占用比例 (0.0-1.0，默认0.9即90%)
        duration: 持续时间（秒），None表示一直运行直到手动停止
        matrix_size: 矩阵大小，用于计算负载（默认10000）
    """
    try:
        # 设置使用的GPU
        torch.cuda.set_device(gpu_id)
        device = torch.device(f'cuda:{gpu_id}')

        # 获取GPU总显存
        props = torch.cuda.get_device_properties(gpu_id)
        total_memory = props.total_memory
        target_memory = int(total_memory * memory_ratio)

        print(f"[GPU {gpu_id}] 开始占用显卡: {props.name}")
        print(f"[GPU {gpu_id}] 总显存: {total_memory / (1024**3):.2f} GB")
        print(f"[GPU {gpu_id}] 目标占用: {target_memory / (1024**3):.2f} GB ({memory_ratio*100}%)")
        print(f"[GPU {gpu_id}] 矩阵大小: {matrix_size}x{matrix_size}")
        if duration:
            print(f"[GPU {gpu_id}] 持续时间: {duration} 秒")
        else:
            print(f"[GPU {gpu_id}] 持续时间: 直到手动停止 (Ctrl+C)")
        print()

        # 创建大矩阵占用显存
        allocated_tensors = []
        allocated_memory = 0

        # 估算每个矩阵占用的显存（float32, 4 bytes per element）
        bytes_per_matrix = matrix_size * matrix_size * 4

        print(f"[GPU {gpu_id}] 正在分配显存...")
        while allocated_memory < target_memory:
            try:
                tensor = torch.randn(matrix_size, matrix_size, device=device)
                allocated_tensors.append(tensor)
                allocated_memory += bytes_per_matrix

                current_gb = allocated_memory / (1024**3)
                target_gb = target_memory / (1024**3)
                progress = (allocated_memory / target_memory) * 100
                print(f"[GPU {gpu_id}] 已分配: {current_gb:.2f}/{target_gb:.2f} GB ({progress:.1f}%)", end='\r')

            except RuntimeError as e:
                if "out of memory" in str(e):
                    print(f"\n[GPU {gpu_id}] 已达到显存上限")
                    break
                else:
                    raise

        print(f"\n[GPU {gpu_id}] 显存分配完成！")
        print(f"[GPU {gpu_id}] 实际占用: {allocated_memory / (1024**3):.2f} GB")

        # 开始计算负载
        print(f"[GPU {gpu_id}] 开始密集计算...")
        start_time = time.time()
        iteration = 0

        try:
            while True:
                # 进行矩阵乘法运算，保持GPU利用率
                for i in range(min(len(allocated_tensors) - 1, 5)):  # 限制运算次数避免过载
                    result = torch.matmul(allocated_tensors[i], allocated_tensors[i+1])
                    # 同步等待计算完成
                    torch.cuda.synchronize()

                iteration += 1
                elapsed = time.time() - start_time

                # 每5秒输出一次状态
                if iteration % 50 == 0:
                    mem_allocated = torch.cuda.memory_allocated(gpu_id) / (1024**3)
                    mem_reserved = torch.cuda.memory_reserved(gpu_id) / (1024**3)
                    print(f"[GPU {gpu_id}] 运行中... 已运行 {elapsed:.1f}秒 | "
                          f"显存: {mem_allocated:.2f}GB (保留: {mem_reserved:.2f}GB) | "
                          f"迭代: {iteration}")

                # 检查是否超时
                if duration and elapsed >= duration:
                    print(f"\n[GPU {gpu_id}] 已达到指定时间 {duration} 秒")
                    break

        except KeyboardInterrupt:
            print(f"\n[GPU {gpu_id}] 接收到停止信号 (Ctrl+C)")

        # 清理
        print(f"[GPU {gpu_id}] 正在清理显存...")
        del allocated_tensors
        torch.cuda.empty_cache()
        print(f"[GPU {gpu_id}] 清理完成")

    except Exception as e:
        print(f"\n[GPU {gpu_id}] 错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description='GPU 负载测试工具 - 占满指定GPU进行测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 占满 GPU 0，使用90%显存
  python test_gpu_load.py -g 0

  # 占满 GPU 1，使用80%显存，持续运行300秒
  python test_gpu_load.py -g 1 -m 0.8 -d 300

  # 占满多个GPU（使用逗号分隔）
  python test_gpu_load.py -g 0,1,2 -m 0.85

  # 使用小矩阵（适合小显存GPU）
  python test_gpu_load.py -g 0 -s 5000

  # 使用大矩阵（适合大显存GPU）
  python test_gpu_load.py -g 0 -s 15000

提示:
  - 按 Ctrl+C 可以随时停止
  - 默认占用90%显存，可以根据需要调整
  - 矩阵大小影响显存分配粒度，默认10000适合大多数情况
        """
    )

    parser.add_argument('-g', '--gpu', type=str, required=True,
                        help='GPU ID，多个GPU用逗号分隔 (例如: 0 或 0,1,2)')
    parser.add_argument('-m', '--memory', type=float, default=0.9,
                        help='显存占用比例 (0.0-1.0，默认0.9即90%%)')
    parser.add_argument('-d', '--duration', type=int, default=None,
                        help='持续时间（秒），不指定则一直运行')
    parser.add_argument('-s', '--size', type=int, default=10000,
                        help='矩阵大小 (默认10000，可调整为5000-20000)')

    args = parser.parse_args()

    # 验证参数
    if args.memory <= 0 or args.memory > 1:
        print("错误：显存占用比例必须在 0.0-1.0 之间")
        sys.exit(1)

    if args.size < 1000 or args.size > 50000:
        print("错误：矩阵大小必须在 1000-50000 之间")
        sys.exit(1)

    # 显示GPU信息
    gpu_count = get_gpu_info()

    # 解析GPU ID
    try:
        gpu_ids = [int(x.strip()) for x in args.gpu.split(',')]
    except ValueError:
        print("错误：无效的GPU ID格式")
        sys.exit(1)

    # 验证GPU ID
    for gpu_id in gpu_ids:
        if gpu_id < 0 or gpu_id >= gpu_count:
            print(f"错误：GPU {gpu_id} 不存在（可用范围: 0-{gpu_count-1}）")
            sys.exit(1)

    # 单GPU模式
    if len(gpu_ids) == 1:
        occupy_gpu(gpu_ids[0], args.memory, args.duration, args.size)

    # 多GPU模式（多进程）
    else:
        import multiprocessing as mp

        print(f"将在 {len(gpu_ids)} 个GPU上运行: {gpu_ids}")
        print("提示：每个GPU会在独立进程中运行")
        print()

        processes = []
        for gpu_id in gpu_ids:
            p = mp.Process(
                target=occupy_gpu,
                args=(gpu_id, args.memory, args.duration, args.size)
            )
            p.start()
            processes.append(p)
            time.sleep(1)  # 错开启动时间

        # 等待所有进程完成
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            print("\n接收到停止信号，正在终止所有进程...")
            for p in processes:
                p.terminate()
                p.join()

        print("\n所有GPU测试完成")


if __name__ == '__main__':
    main()
