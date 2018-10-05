#!/usr/bin/python3.4

from sys import argv

size_tlb = 16           # Lab Req
page_size = 256         # Lab Req
frame_size = 256        # Lab Req
offset_bits = 0xFF      # log2(page_size) = # bits for offset, want LSB
addr_bits = 0xFF00      # log2(frame_num) = # bits for addr, want 8 MSB
block_size = 256        # Lab Req

num_addr_translated = 0
page_faults = 0
page_fault_rate = 0.0
tlb_hits = 0
tlb_misses = 0
tlb_hit_rate = 0.0

tlb = []                # tlb holds tuple (page #, frame #)
page_table = []         # page table holds tuple (page #, frame #)
RAM = []                # RAM holds # frames X frame size
                        # Disk is represented by backing_stores

def main():
    addresses_f, frame_num, alg = check_args()

    addresses = open(addresses_f, 'r')
    backing_store = open('BACKING_STORE.bin', 'rb')

    init(frame_num)

    enforce_alg(addresses, backing_store, alg)

    addresses.close()
    backing_store.close()


def enforce_alg(addresses, backing_store, alg):
    global num_addr_translated
    global page_fault_rate
    global tlb_hit_rate
    global page_faults 
    global tlb_hits 
    global tlb_misses 

    for addr in addresses:
        addr = int(addr)
        translate_page(addr, backing_store)
        num_addr_translated += 1

    page_fault_rate = page_faults/num_addr_translated
    tlb_hit_rate = tlb_hits/num_addr_translated

    print('Number of Translated Addresses =', num_addr_translated)
    print('Page Faults =', page_faults)
    print('Page Fault Rate = %.3f' % page_fault_rate)
    print('TLB Hits =', tlb_hits)
    print('TLB Misses =', tlb_misses)
    print('TLB Hit Rate = %.3f' % tlb_hit_rate)


# First check TLB, then check page_table
def translate_page(addr, backing_store):
    global page_faults 
    global tlb_hits 
    global tlb_misses 

    global tlb 
    global page_table
    global RAM
    
    page_number = (addr & addr_bits) >> 8
    offset = (addr & offset_bits)

    frame_number = -1

    # TLB
    for i in range(len(tlb)):
        if(tlb[i][0] == page_number):
            frame_number = tlb[i][1]
            tlb_hits += 1

    # TLB miss
    if(frame_number == -1):
        tlb_misses += 1
        # Page Table
        for i in range(len(page_table)):
            if(page_table[i][0] == page_number):
                frame_number = page_table[i][1]

        #Page Table Miss
        if(frame_number == -1):
            pt_index = read_disk(page_number, backing_store)
            page_faults += 1
            frame_number = page_table[pt_index][1]

    tlb_insert(page_number, frame_number)
    value = RAM[frame_number][offset]
    if value > 127:
        value -= 256

    frame_data = RAM[frame_number]
    printable_frame_d = ''
    for ch in frame_data:
        printable_frame_d += str(hex(ch).upper()).format('{:02X}')[2:].zfill(2)

    print('{}, {}, {}, {}'.format(addr, value, frame_number, printable_frame_d))

# FIFO insert/replacement for TLB
def tlb_insert(page_number, frame_number):
    for i in range(len(tlb)):
        if(tlb[i][0] == page_number):
            temp = tlb.pop(i)
            temp.append([-1, -1])
            end_of_queue = get_next_tlb()
            tlb.insert(end_of_queue, temp)
            return

    end_of_queue = get_next_tlb()

    if(end_of_queue < size_tlb):
        tlb[end_of_queue][0] = page_number
        tlb[end_of_queue][1] = frame_number
    else:
        tlb.pop(0)
        tlb.append([page_number, frame_number])


# Find next empty index in TLB, or last index
def get_next_tlb():
    for i in range(len(tlb)):
        if(tlb[i][0] == -1):
            return i
    return len(tlb)-1

# Page fault occurreed, need to find value from disk
def read_disk(page_number, backing_store):
    global page_table
    global RAM

    backing_store.seek(page_number*block_size)
    data = backing_store.read(block_size)

    available_page = get_next_page()
    available_frame = get_next_frame()

    for i in range(block_size):
        RAM[available_frame][i] = data[i]

    page_table[available_page][0] = page_number
    page_table[available_page][1] = available_frame


    return available_page

# Find next empty index in page_table
def get_next_page():
    for i in range(len(page_table)):
        if(page_table[i][0] == -1):
            return i
    return -1

# Find next empty index in memory
def get_next_frame():
    for i in range(len(RAM)):
        flag = 1
        for j in range(len(RAM[i])):
            if(RAM[i][j] != -1):
                flag = 0
        if(flag == 1):
            return(i)
    return -1

# Initialize tlb , page table, and memory according to provided frame_num
def init(frame_num):
    for i in range(size_tlb):
        tlb.append([-1, -1])
    
    for i in range(page_size):
        page_table.append([-1, -1])

    for i in range(frame_num):
        RAM.append([])
        for j in range(frame_size):
            RAM[i].append(-1)


def check_args():
    argc = len(argv)

    if((argc > 4) | (argc < 2)):
        print("Usage: python3 memSim.py <reference-sequence-file.txt> [<FRAMES> [<PRA>]]")
        exit()
    elif(argc == 3):
        if(is_proper_frame(argv[2])):
            return argv[1], argv[2], 'FIFO'
        else:
            print("Usage: 0 < int(Frames) <= 256")
            exit()

    elif(argc == 2):
        return argv[1], 256, 'FIFO'

    if(is_proper_frame_size(argv[2])):
        if((argv[3] == 'FIFO') | (argv[3] == 'LRU') | (argv[3] == 'OPT') ):
            return argv[1], argv[2], argv[3]
        else:
            print("Usage: PRA must be either FIFO, LRU, or OPT")
            exit()
    else:
        print("Usage: 0 < int(Frames) <= 256")
        exit()

def is_proper_frame_size(s):
    n = 0
    try:
        n = int(s)
    except ValueError:
        return False
    if((n > 0) & (n <= 256)):
        return True
    else:
        return False

if __name__ == '__main__':
    main()
