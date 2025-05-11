#!/usr/bin/env python3
# run the script: python -m parrot_project.experiment_3.simulate
"""
Simulate Parrot Experiment 3: defender assisted by neighbor.
This experiment is run in the same SJA1000 USB adapters, but the difference
is that the Defender (Alice) is supported by another ECU
which sends non-spoofed messages, in order to create 'benign traffic'.
With this help Alice is able to achieve 100% BUS OFF, and actually the script
runs until the ECUs are bus off
"""
import heapq
import matplotlib.pyplot as plt

from  ..utils import (
    ErrorStates,
    CanNode,
    CanBusBase,
    ASSISTANT_GAP_US, ATTACKER_PERIOD_US, GAP_US
)

class CanBus(CanBusBase):
    def __init__(self):
        super().__init__(log_file="exp_3.txt")
        self.assistant = CanNode("[C] ASSISTANT")  # C: Assistant
        self.history = {"time": [], "attacker": [], "defender": [], "assistant": []}
    
    def execute(self):
        # Schedule Attacker’s periodic spoof
        self.schedule(0, self.__send_attack)
        # Schedule Assistant’s continuous AD-messages
        self.schedule(0, self.__assistant_send)
        # Run until no events or Attacker is bus-off
        while self.events and self.attacker.state != ErrorStates.BUS_OFF:
            t, _, callback = heapq.heappop(self.events)
            self.time_us = t
            self.__record_history()
            callback()
        self.log_f.close()
        # after simulation ends, plot the TEC history
        self.__make_plot()

        return

    def __record_history(self):
        self.record_history()
        self.history["assistant"].append(self.assistant.TEC)

    def __make_plot(self):
        """
        Plot the TEC history for attacker, defender and assistant.
        """
        plt.figure()
        plt.plot(self.history["time"], self.history["attacker"],   marker='o', label="[E]")
        plt.plot(self.history["time"], self.history["defender"], marker='s', label="[A]")
        plt.plot(self.history["time"], self.history["assistant"], marker='^', label="[C]")
        plt.xlabel("Time (us)")
        plt.ylabel("Transmit Error Counter (TEC)")
        plt.title("TEC Evolution: Parrot Experiment 3")
        plt.legend()
        plt.grid(True)
        output_file = "plot_3.png"
        plt.savefig(output_file)
        print(f"Plot saved to {output_file}")

    def __send_attack(self):
        self.log("sends spoofed frame", self.attacker)
        self.schedule(0, self.__handle_collision)
        if self.attacker.state == ErrorStates.ACTIVE:
            self.schedule(ATTACKER_PERIOD_US, self.__send_attack)

    def __handle_collision(self):
        self.attacker.collide()
        self.log("collision bit-error", self.attacker)
        self.defender.collide()
        self.log("collision bit-error", self.defender)
        if self.attacker.state == ErrorStates.ACTIVE:
            self.schedule(GAP_US, self.__handle_collision)
        else:
            self.schedule(GAP_US, self.__recover_defender)

    def __recover_defender(self):
        self.defender.succeed()
        self.log("recovers send", self.defender)
        if self.defender.state != ErrorStates.ACTIVE:
            self.schedule(GAP_US, self.__recover_defender)
        else:
            self.log("back ACTIVE", self.defender)
            self.schedule(0, self.__collide_passive)

    def __collide_passive(self):
        self.attacker.collide()
        self.log("passive-flag collision", self.attacker)
        if self.attacker.state != ErrorStates.BUS_OFF:
            next_gap = min(ASSISTANT_GAP_US, GAP_US)
            self.schedule(next_gap, self.__collide_passive)
        else:
            self.log("bus-off reached", self.attacker)

    def __assistant_send(self):
        self.log("sends AD-message", self.assistant)
        if self.attacker.state != ErrorStates.BUS_OFF:
            self.schedule(ASSISTANT_GAP_US, self.__assistant_send)

# start execution
if __name__ == "__main__":
    CanBus().execute()
