"""
This is a base helper file utilized by the experiment scripts.

It contains some constants and other classes such as ErrorStates, CanNode, and CanBusBase.

To schedule and dispatch the events we used heapq, which handles
collision retries, recovery sends, round starts in chronological order.
"""
import os
from enum import Enum
import heapq
import matplotlib.pyplot as plt

# Gaps in microseconds
GAP_US = 31 # Defender’s D-frame gap (SJA1000 max speed), Alice can't send msgs more frequently because this gap is required 
MAX_ROUNDS = 3 # number of attack/recovery cycles (chosen for test)

ASSISTANT_GAP_US   = 200       # Assistant’s AD-message gap (~200µs)
ATTACKER_PERIOD_US = 1_000_000 # Attacker’s spoof period (1 s)

# Error states
class ErrorStates(Enum):
    ACTIVE = "ACTIVE"
    ERROR_PASSIVE = "PASSIVE"
    BUS_OFF = "BUS-OFF"

# CAN node refers to the ECU entities (Attacker/Defender or Eve/Alice)
class CanNode:
    def __init__(self, name: str):
        self.name = name
        self.TEC = 0
        self.state = ErrorStates.ACTIVE

    def collide(self):
        # Increases the transmit error counter by 8
        # and updates the ECU's state.
        self.TEC += 8
        self._update_state()

    def succeed(self):
        # Decreases the transmit error counter by 1
        # and updates the ECU's state.
        if self.TEC > 0:
            self.TEC -= 1
        self._update_state()

    def _update_state(self):
        if self.TEC >= 256:
            self.state = ErrorStates.BUS_OFF
        elif self.TEC >= 128:
            self.state = ErrorStates.ERROR_PASSIVE
        else:
            self.state = ErrorStates.ACTIVE


# Can Bus Base class, extended by the ex 1 and ex3 classes
class CanBusBase:
    def __init__(self, log_file):
        self.time_us = 0
        self.events = []
        self.counter = 0
        self.rounds = 0 # -----
        
        # create nodes (ECU simulation)
        self.attacker = CanNode("[E] ATTACKER")   # E: Attacker
        self.defender = CanNode("[A] DEFENDER")   # A: Defender
        # record TEC history
        self.history = {"time": [], "attacker": [], "defender": []}

        # make a log dir and set the log file up
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        full_path = os.path.join(logs_dir, log_file)

        self.log_f = open(full_path, "w", encoding="utf-8")
        header = "TIME (us)   |  EVENT                          | TEC/STATE"
        sep = "-" * len(header)
        print(header)
        print(sep)

        self.log_f.write(header + "\n" + sep + "\n")

    def schedule(self, delay_us: int, callback):
        """
        Schedule a simulation event to occur after a given delay.
        #note: time_us means time in micro seconds (us -> microseconds)
        Internally, uses a heapq-based priority queue (`self.events`) where each event is stored
        as a tuple (event_time, order, callback). `event_time` is the simulated timestamp
        (current time_us + delay_us), and `order` (self.counter) is a running counter used as a
        tie-breaker so that events scheduled for the same timestamp execute in FIFO order.
        The `callback` is the function to invoke when the event fires.
        """
        event_time = self.time_us + delay_us
        heapq.heappush(self.events, (event_time, self.counter, callback))
        self.counter += 1

    def log(self, event: str, node: CanNode=None):
        ts = f"{self.time_us}us"
        if node:
            info = f"TEC:{node.TEC} [{node.state.value}]"
            line = f"{ts:>12} | {event:<30} | {info}"
        else:
            line = f"{ts:>12} | {event}"
        print(line)
        self.log_f.write(line + "\n")

    def record_history(self):
        """
        Record current TEC values of attacker and defender at the current time.
        """
        self.history["time"].append(self.time_us)
        self.history["attacker"].append(self.attacker.TEC)
        self.history["defender"].append(self.defender.TEC)
