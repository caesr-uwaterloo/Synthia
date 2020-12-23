# Synthia
Automated tool for constructing predictable and high-performance snooping-bus based protocol implementations

## Usage
`synthia.py` is the main python script.
`python3 synthia.py -i <input spec file> -s <memory model>`

We have provided protocol specification files for different protocols. These specifications are at the private cache level. There are two memory models: `direct` where cores can communicate data with other cores directly using point-to-point interconnects and `memory` where all communication between cores is through the shared memory.

## Contact
For questions/concerns about Synthia, please feel free to reach out at amkaushi@uwaterloo.ca
