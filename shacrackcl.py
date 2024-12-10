import pyopencl as cl
import numpy as np
import datetime
import sys
import itertools

# OpenCL kernel for SHA-1 computation
SHA1_KERNEL = """
// SHA-1 constants
#define SHA1_A 0x67452301
#define SHA1_B 0xEFCDAB89
#define SHA1_C 0x98BADCFE
#define SHA1_D 0x10325476
#define SHA1_E 0xC3D2E1F0

// Rotate left operation
#define ROL(x, n) (((x) << (n)) | ((x) >> (32-(n))))

// SHA-1 round functions
#define F1(b,c,d) (((b) & (c)) | ((~(b)) & (d)))
#define F2(b,c,d) ((b) ^ (c) ^ (d))
#define F3(b,c,d) (((b) & (c)) | ((b) & (d)) | ((c) & (d)))

__kernel void sha1_crack(
    __global const char* charset,
    int word_length,
    __global const char* target_hash,
    __global char* result,
    __global int* found
) {
    int gid = get_global_id(0);
    
    // Generate combination for this work item
    char current[16] = {0};  // Max length 16
    int temp = gid;
    
    for(int i = 0; i < word_length; i++) {
        current[i] = charset[temp % 26];
        temp /= 26;
    }
    
    // SHA-1 computation
    uint w[80];
    uint a, b, c, d, e, f, k, temp;
    
    // Initialize message block
    for(int i = 0; i < 16; i++) {
        w[i] = 0;
    }
    
    // Copy input to message block
    for(int i = 0; i < word_length; i++) {
        w[i/4] |= (uint)current[i] << ((3-(i%4))*8);
    }
    
    // Add padding
    w[word_length/4] |= 0x80 << ((3-(word_length%4))*8);
    w[15] = word_length * 8;
    
    // Message schedule
    for(int i = 16; i < 80; i++) {
        w[i] = ROL(w[i-3] ^ w[i-8] ^ w[i-14] ^ w[i-16], 1);
    }
    
    // Initialize hash values
    a = SHA1_A;
    b = SHA1_B;
    c = SHA1_C;
    d = SHA1_D;
    e = SHA1_E;
    
    // Main loop
    for(int i = 0; i < 80; i++) {
        if(i < 20) {
            f = F1(b,c,d);
            k = 0x5A827999;
        } else if(i < 40) {
            f = F2(b,c,d);
            k = 0x6ED9EBA1;
        } else if(i < 60) {
            f = F3(b,c,d);
            k = 0x8F1BBCDC;
        } else {
            f = F2(b,c,d);
            k = 0xCA62C1D6;
        }
        
        temp = ROL(a,5) + f + e + k + w[i];
        e = d;
        d = c;
        c = ROL(b,30);
        b = a;
        a = temp;
    }
    
    // Final hash
    uint hash[5];
    hash[0] = SHA1_A + a;
    hash[1] = SHA1_B + b;
    hash[2] = SHA1_C + c;
    hash[3] = SHA1_D + d;
    hash[4] = SHA1_E + e;
    
    // Convert to hex and compare
    char hex[41] = {0};
    for(int i = 0; i < 5; i++) {
        for(int j = 0; j < 8; j++) {
            int val = (hash[i] >> (28-j*4)) & 0xf;
            hex[i*8+j] = val < 10 ? '0' + val : 'a' + (val-10);
        }
    }
    
    // Compare with target
    bool match = true;
    for(int i = 0; i < 40; i++) {
        if(hex[i] != target_hash[i]) {
            match = false;
            break;
        }
    }
    
    if(match) {
        *found = 1;
        for(int i = 0; i < word_length; i++) {
            result[i] = current[i];
        }
    }
}
"""

def main():
    if len(sys.argv) != 2:
        print("Usage: python shacrack_opencl.py <SHA-1 hash value>")
        sys.exit(1)
        
    target_hash = sys.argv[1].lower()
    
    # Initialize OpenCL
    platforms = cl.get_platforms()
    intel_platform = None
    
    # Find Intel platform
    for platform in platforms:
        if 'intel' in platform.name.lower():
            intel_platform = platform
            break
            
    if intel_platform is None:
        print("No Intel GPU platform found")
        sys.exit(1)
        
    # Get GPU device
    gpu_devices = intel_platform.get_devices(device_type=cl.device_type.GPU)
    if not gpu_devices:
        print("No Intel GPU device found")
        sys.exit(1)
        
    # Create context and command queue
    context = cl.Context([gpu_devices[0]])
    queue = cl.CommandQueue(context)
    
    # Build program
    program = cl.Program(context, SHA1_KERNEL).build()
    
    # Prepare constant buffers
    charset = 'abcdefghijklmnopqrstuvwxyz'
    charset_buf = cl.Buffer(context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, 
                          hostbuf=np.frombuffer(charset.encode(), dtype=np.uint8))
    target_buf = cl.Buffer(context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                          hostbuf=np.frombuffer(target_hash.encode(), dtype=np.uint8))
    
    start_time = datetime.datetime.now()
    
    # Try different word lengths
    for word_length in range(1, 16):
        # Calculate total combinations for this length
        total_combinations = 26 ** word_length
        
        # Prepare output buffers
        result_buf = cl.Buffer(context, cl.mem_flags.WRITE_ONLY, size=16)
        found_buf = cl.Buffer(context, cl.mem_flags.READ_WRITE, size=4)
        
        # Clear found flag
        cl.enqueue_fill_buffer(queue, found_buf, np.array([0], dtype=np.int32), 0, 4)
        
        # Set kernel arguments
        kernel = program.sha1_crack
        kernel.set_args(charset_buf, np.int32(word_length), target_buf, result_buf, found_buf)
        
        # Execute kernel
        global_size = (total_combinations,)
        local_size = None  # Let OpenCL choose the work-group size
        
        event = cl.enqueue_nd_range_kernel(queue, kernel, global_size, local_size)
        event.wait()
        
        # Check if solution found
        found = np.zeros(1, dtype=np.int32)
        cl.enqueue_copy(queue, found, found_buf)
        
        if found[0]:
            # Read result
            result = np.zeros(16, dtype=np.uint8)
            cl.enqueue_copy(queue, result, result_buf)
            result_str = bytes(result[:word_length]).decode('ascii')
            
            end_time = datetime.datetime.now()
            print("SHA-1 input:", result_str)
            print("Time for breaking:", end_time - start_time)
            sys.exit(0)
    
    print("No match found")

if __name__ == '__main__':
    main()