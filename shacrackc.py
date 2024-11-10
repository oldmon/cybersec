import datetime
import itertools
import hashlib
import multiprocessing
import sys
from multiprocessing import Pool

def process_chunk(args):
    """Process a chunk of combinations and return result if found"""
    start_index, chunk_size, total_combinations, words, target_hash = args
    
    # Generate only this worker's portion of combinations
    for i, combination in enumerate(itertools.product('abcdefghijklmnopqrstuvwxyz', repeat=words)):
        if i < start_index:
            continue
        if i >= start_index + chunk_size:
            break
            
        bruteinput = ''.join(combination)
        s = hashlib.sha1()
        s.update(bruteinput.encode("utf-8"))
        h = s.hexdigest()
        
        if h == target_hash:
            return bruteinput
    return None

def parallel_combinations(words, target_hash, num_processes):
    """Split work across multiple processes"""
    # Calculate total combinations for this word length
    total_combinations = 26 ** words
    
    # Calculate chunk size for each process
    chunk_size = total_combinations // num_processes + 1
    
    # Create list of arguments for each process
    process_args = []
    for i in range(0, total_combinations, chunk_size):
        process_args.append((i, chunk_size, total_combinations, words, target_hash))
    
    # Create process pool and map work
    with Pool(processes=num_processes) as pool:
        results = pool.map(process_chunk, process_args)
        
    # Check if any process found the match
    for result in results:
        if result is not None:
            return result
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python shacrack.py <SHA-1 hash value>")
        sys.exit(1)

    target_hash = sys.argv[1]
    num_cores = multiprocessing.cpu_count()
    start_time = datetime.datetime.now()
    
    # Try different word lengths
    for words in range(1, 16):
        result = parallel_combinations(words, target_hash, num_cores)
        if result:
            end_time = datetime.datetime.now()
            print("SHA-1 input:", result)
            print("Time for breaking:", end_time - start_time)
            sys.exit(0)
            
    print("No match found")

if __name__ == '__main__':
    main()