import itertools
import sys
import multiprocessing

def generate_combinations(length):
    for combination in itertools.product('abcdefghijklmnopqrstuvwxyz', repeat=length):
        print(''.join(combination))


def worker(num):
    # Perform CPU-intensive task here
    result = ...
    return result

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python script.py <length>")
        sys.exit(1)

    length = int(sys.argv[1])
    generate_combinations(length)
    pool = multiprocessing.Pool()
    results = pool.map(worker, range(num_cores))