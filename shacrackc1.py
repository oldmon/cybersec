import datetime
import itertools
import hashlib
import multiprocessing
from multiprocessing import Pool, Manager
import sys
import time
import signal

def init_worker():
    """Initialize worker process to ignore SIGINT"""
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def process_chunk(args):
    """Process a chunk of combinations and report progress"""
    start_index, chunk_size, total_combinations, words, target_hash, progress_dict = args
    last_update = time.time()
    update_interval = 0.5
    
    try:
        for i, combination in enumerate(itertools.product('abcdefghijklmnopqrstuvwxyz', repeat=words)):
            if i < start_index:
                continue
            if i >= start_index + chunk_size:
                break
                
            bruteinput = ''.join(combination)
            
            current_time = time.time()
            if current_time - last_update > update_interval:
                with progress_dict['lock']:
                    progress_dict['completed_count'] = max(
                        progress_dict['completed_count'],
                        start_index + (i - start_index)
                    )
                last_update = current_time
            
            s = hashlib.sha1()
            s.update(bruteinput.encode("utf-8"))
            h = s.hexdigest()
            
            if h == target_hash:
                progress_dict['found'] = bruteinput
                return bruteinput
    except:
        return None
    return None
    
def status_printer(progress_dict, start_time, total_combinations):
    """Print status updates from a separate process"""
    while True:
        try:
            found = progress_dict.get('found', None)
            if progress_dict.get('done', False):
                break
            
            elapsed = datetime.datetime.now() - start_time
            completed = progress_dict.get('completed_count', 0)
            progress = (completed / total_combinations) * 100 if total_combinations > 0 else 0
            
            # 移除 Length 顯示，只保留時間和進度
            print(f"\rTime: {elapsed} | Progress: {progress:.2f}%", 
                  end='', flush=True)
            
            if found:
                print()
                break
            
            time.sleep(0.2)
            
        except (KeyboardInterrupt, SystemExit):
            break

def parallel_combinations(words, target_hash, num_processes, progress_dict):
    """Split work across multiple processes"""
    total_combinations = 26 ** words
    chunk_size = total_combinations // num_processes + 1
    
    progress_dict['completed_count'] = 0
    
    process_args = []
    for i in range(0, total_combinations, chunk_size):
        process_args.append((i, chunk_size, total_combinations, words, target_hash, progress_dict))
    
    with Pool(processes=num_processes, initializer=init_worker) as pool:
        try:
            results = pool.map_async(process_chunk, process_args)
            # 等待結果，但允許中斷
            while not results.ready():
                try:
                    results.wait(timeout=0.2)
                except KeyboardInterrupt:
                    print("\nStopping processes...", flush=True)
                    pool.terminate()
                    pool.join()
                    raise KeyboardInterrupt
            
            for result in results.get():
                if result is not None:
                    return result
        except KeyboardInterrupt:
            raise
    return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python shacrack.py <SHA-1 hash value>")
        sys.exit(1)

    target_hash = sys.argv[1]
    num_cores = multiprocessing.cpu_count()
    start_time = datetime.datetime.now()
    
    with Manager() as manager:
        progress_dict = manager.dict()
        progress_dict['lock'] = manager.Lock()
        progress_dict['completed_count'] = 0
        printer_process = None
        
        try:
            print(f"Starting search using {num_cores} CPU cores...")
            for words in range(1, 16):
                progress_dict['word_length'] = words
                total_combinations = 26 ** words
                
                print(f"\nTrying length {words} ({total_combinations:,} combinations)...")
                
                printer_process = multiprocessing.Process(
                    target=status_printer,
                    args=(progress_dict, start_time, total_combinations)
                )
                printer_process.start()
                
                try:
                    result = parallel_combinations(words, target_hash, num_cores, progress_dict)
                    progress_dict['done'] = True
                    printer_process.join(timeout=1)
                    progress_dict['done'] = False
                    
                    if result:
                        end_time = datetime.datetime.now()
                        print(f"\nSHA-1 input: {result}")
                        print(f"Time for breaking: {end_time - start_time}")
                        break
                except KeyboardInterrupt:
                    break
            else:
                print("\nNo match found")
                
        except KeyboardInterrupt:
            print("\nSearch interrupted by user")
        finally:
            progress_dict['done'] = True
            if printer_process and printer_process.is_alive():
                printer_process.join(timeout=1)
                if printer_process.is_alive():
                    printer_process.terminate()
            print("\nCleanup complete")

if __name__ == '__main__':
    main()