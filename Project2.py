class Process:
    def __init__(self, pid, arrival_time, lifetime, address_space):
        self.pid = pid # Unique process id
        self.arrival_time = arrival_time # The time process arives at the simulator
        self.lifetime = lifetime # How long the process will run after it starts
        self.address_space = address_space # How much memory the process needs in the simulator
        self.start_time = None # The time at which the process was allocated memory
        self.completion_time = None # The time at which the process finished (startime + lifetime)


class MemorySimulator:
    """ Constructor to declare the simulator with respective parameters"""
    def __init__(self, memory_size, policy, policy_param):
        self.memory_size = memory_size # Memory available for simulation
        self.policy = policy # VSP/PAG/SEG
        self.policy_param = policy_param # which policy to use
        self.time = 0 # Clock to keep track of time 
        self.process_queue = [] # List of processess waiting to be allocated (only the arrival processes)
        self.memory_map = []  # (start, end, pid, page_num)
        self.event_queue = [] # contains arrived and completed processes
        self.completed_processes = [] # List of processes which are finished and longer in memory

    """ Function the retrieve parameters from input file"""
    def open_file(self, filename):
        with open(filename, 'r') as f:
            n = int(f.readline().strip()) # Reading the first line and convert to int (n = number of processes)
            for _ in range(n): # run the for loop for n number of times
                # For every process
                pid = int(f.readline().strip()) # Read the process id
                arrival, lifetime = map(int, f.readline().strip().split()) # Read the arrival and lifetime
                address_space = list(map(int, f.readline().strip().split()))[1:] # skips the count and creates an adress space list
                process = Process(pid, arrival, lifetime, address_space) # Create a process with all the parameters
                self.event_queue.append((arrival, 'arrival', process)) # Adds the proces to the queue along with arival time with arrival status
                f.readline() # Skips the empty line between processes

    """ Function to run the simulator"""
    def run(self):
        # Run as along as there are processes present in event queue or process queue
        while self.event_queue or self.process_queue:
            self.process_events() # process the events
            self.try_allocate_memory() #try to allocate memory if possible
            self.time += 1 # add to time
            if self.time > 100000: # If time goes beyond 100000 then stop as instructed in the pdf
                break
        self.final_report() # Print the average turnaround time to the screen

    def process_events(self):
        time_record = [] # Array for time recording
        tab = False # boolean variable to keep track of a tab formatting
        arrivals = [] # declare a array for processes that arrive
        completions = [] # declare a array for processes that are complete
        for event in list(self.event_queue): # Goes through all the processes that arrived in event queue
            event_time, event_type, process = event # event_time is the arrival time, event_type is arrival / completetion
            if event_time == self.time: # If arrival time of process is equal to current time, if not the process hasn't arrived yet
                if event_type == 'arrival': 
                    arrivals.append((event_type, process)) # if the process is arrival type add it to arrival array
                elif event_type == 'completion':
                    completions.append((event_type, process)) # else add it to completion array
                self.event_queue.remove(event) # now that event is processed remove it from the events_queue

        for _, process in arrivals:
            if self.time not in time_record: # formatting for printing
                if self.time == 0:
                    print(f"t = {self.time}: ", end="")
                else:
                    print(f"\t")
                    print(f"t = {self.time}: ", end="")
                tab = False

            time_record.append(self.time)
            if tab == False:
                print(f"Process {process.pid} arrives") 
            else:
                print(f"\tProcess {process.pid} arrives") 
            tab = True
            self.process_queue.append(process) # add the process to process list for waiting to be allocated
            print(f"\tInput Queue:[{' '.join(str(p.pid) for p in self.process_queue)}]")

        for _, process in completions: 
            if self.time not in time_record: # formatting for printing
                print(f"\t")
                print(f"t = {self.time}: ", end="")
                tab = False

            time_record.append(self.time)
            if tab == False:
                print(f"Process {process.pid} completes") 
            else:
                print(f"\tProcess {process.pid} completes")
            tab = True

            process.completion_time = self.time # process completetion time is current time when process finished
            self.completed_processes.append(process) # add it to list of completed processes
            self.release_memory(process) # free up memory

    def try_allocate_memory(self):
        for process in list(self.process_queue): # processes that have arrived
            if sum(process.address_space) > self.memory_size:
                continue # If the memory needed for process is more than simulator memory skip it
            if self.allocate_memory(process): # process goes for allocation
                self.process_queue.remove(process)
                process.start_time = self.time 
                self.event_queue.append((self.time + process.lifetime, 'completion', process)) # process has gone through the allocation and completed
                print(f"\tMM moves Process {process.pid} to memory")
                print(f"\tInput Queue:[{' '.join(str(p.pid) for p in self.process_queue)}]") # print the processes in the queue
                print(f"\tMemory Map: ")
                self.print_memory_map() 

    def allocate_memory(self, process):
        total = sum(process.address_space) # add all the adress spaces
        if self.policy == 1:
            return self.vsp_allocate(process, total) # VSP
        elif self.policy == 2:
            return self.paging_allocate(process, total) # PAG
        elif self.policy == 3:
            return self.segmentation_allocate(process) # SEG
        return False # wrong policy number given

    def vsp_allocate(self, process, size):
        holes = self.get_holes()  # Get list of current holes in memory
        selected = self.select_hole(holes, size) # Choose a hole based on fit strategy
        if selected:
            start, _ = selected
            self.memory_map.append((start, start + size, process.pid, None))
            self.memory_map.sort() # Keep memory map sorted for consistency
            return True
        return False

    def paging_allocate(self, process, size):
        page_size = self.policy_param # Each page is of fixed size
        total_pages = (size + page_size - 1) // page_size # Round up to find how many pages are needed
        holes = self.get_holes()
        frames = []
        # Loop through holes and try to divide them into page-sized frames
        for start, end in holes:
            for addr in range(start, end, page_size):
                if addr + page_size <= end and len(frames) < total_pages:
                    frames.append((addr, addr + page_size))

        if len(frames) == total_pages:
            for i, frame in enumerate(frames):
                self.memory_map.append((frame[0], frame[1], process.pid, i + 1)) # i+1 is the page number
            self.memory_map.sort()
            return True
        return False

    def release_memory(self, process):
        # Remove all memory blocks that belong to this process
        self.memory_map = [entry for entry in self.memory_map if entry[2] != process.pid]
        print(f"\tMemory Map: ")
        self.print_memory_map()

    def get_holes(self):
        holes = []
        used = sorted(self.memory_map) # Sort based on start address
        if not used:
            return [(0, self.memory_size)]
        if used[0][0] > 0: 
            holes.append((0, used[0][0])) # Space before the first block
        for i in range(len(used) - 1):
            if used[i][1] < used[i + 1][0]: # Space between blocks
                holes.append((used[i][1], used[i + 1][0]))
        if used[-1][1] < self.memory_size:
            holes.append((used[-1][1], self.memory_size)) # Space after the last block
        return holes

    def select_hole(self, holes, size):
        eligible = [h for h in holes if h[1] - h[0] >= size] # Filter holes big enough
        if not eligible:
            return None
        if self.policy_param == 1:
            return eligible[0]
        elif self.policy_param == 2:
            return min(eligible, key=lambda h: h[1] - h[0]) # lambda func calculated diff between two
        elif self.policy_param == 3:
            return max(eligible, key=lambda h: h[1] - h[0])
        return None

    def print_memory_map(self):
        segments = []
        prev = 0
        sorted_map = sorted(self.memory_map)
         # Build a full map including holes
        for entry in sorted_map:
            start, end, pid, page_or_segment = entry
            if start > prev:
                segments.append((prev, start, None, None))
            segments.append((start, end, pid, page_or_segment))
            prev = end
        if prev < self.memory_size:
            segments.append((prev, self.memory_size, None, None))
         # Print each segment with proper label
        for start, end, pid, num in segments:
            label = "Free Frame(s)" if self.policy == 2 else "Hole"
            if pid is None:
                print(f"\t\t{start}-{end - 1}: {label}")
            else:
                if self.policy == 2:
                    print(f"\t\t{start}-{end - 1}: Process {pid}, Page {num}")
                elif self.policy == 3:
                    print(f"\t\t{start}-{end - 1}: Process {pid}, Segment {num}")
                else:
                    print(f"\t\t{start}-{end - 1}: Process {pid}")

    def segmentation_allocate(self, process):
        holes = self.get_holes()
        allocations = []
        # Try to allocate memory for each segment
        for idx, segment in enumerate(process.address_space):
            selected = self.select_hole(holes, segment)
            if not selected:
                return False
            start, end = selected
            allocations.append((start, start + segment, idx))
            holes.remove(selected)
            holes.append((start + segment, end)) # Add back the unused remainder
            holes.sort()

        for start, end, idx in allocations:
            self.memory_map.append((start, end, process.pid, idx))
        self.memory_map.sort()
        return True

    def final_report(self):
        # Calculates and prints the average turnaround time at the end of simulation
        completed = [p for p in self.completed_processes if p.completion_time is not None]
        if completed:
            total_turnaround = sum(p.completion_time - p.arrival_time for p in completed)
            avg_turnaround = total_turnaround / len(completed)
            print("\t")
            print(f"Average Turnaround Time: {avg_turnaround:.1f}" if round(avg_turnaround*100)% 10 == 0 else f"Average Turnaround Time: {avg_turnaround:.2f}")

        else:
            print("\t")
            print("Average Turnaround Time: 0.0")


if __name__ == "__main__":
    # asking the user for configuration details
    memory_size = int(input("Memory size: "))
    policy = int(input("Memory management policy (1 - VSP, 2 - PAG, 3 - SEG): "))
    policy_param = int(input("Fit algorithm (1 - first-fit, 2 - best-fit, 3 - worst-fit): ") if policy != 2 else input("Page size: "))
    input_file = input("Workload file: ")

    # declare simulator using the class MemorySimulator using respective parameters
    simulator = MemorySimulator(memory_size, policy, policy_param)

    # Now load the file with the simulator
    simulator.open_file(input_file)

    # run the simulator
    simulator.run()
