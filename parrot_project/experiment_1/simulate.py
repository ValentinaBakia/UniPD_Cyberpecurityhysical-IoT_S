#!/usr/bin/env python3
# run the script: python -m parrot_project.experiment_1.simulate
"""
Simulate Parrot Paper Experiment 1 in an event-driven fashion using heapq.

Per the paper, a single simultaneous spoof (attacker) and D-frame (defender) at t=0
snowballs collisions (+8 TEC each retry) until both ECUs arrive at a ERROR_PASSIVE state (TEC >=128).
After this state the defender ECU continues sending recovery D-frames which decrease the TEC by 1,
and when it reaches a number < 128 the state goes ERROR_ACTIVE again.
This triggers the attacker to send spoofing messages again.

This cycle repeats for MAX_ROUNDS rounds (just to show that this situation keeps repeating 
and the ECUs never reach BUS_OFF state).
All events (collision, recovery, state changes) are logged to console and file,
and TEC history is recorded and plotted at the end.

From this experiment we can understand that the 2 ECUs tested have 0% bus off state
That is because the Defender Alice follows the 31 us gap required by the software
but Eve doesn't because she is a malicious attacker thats why Alice cant make it to put her unit toBUS-OFF
"""
import heapq
import matplotlib.pyplot as plt

from  ..utils import (
    ErrorStates,
    CanNode,
    CanBusBase,
    ASSISTANT_GAP_US,
    ATTACKER_PERIOD_US,
    GAP_US,
    MAX_ROUNDS
)

# Can Bus simulation
class CanBus(CanBusBase):
    def __init__(self):
        super().__init__(log_file="exp_1.txt")
        # since this exp doesnt arrive to BUS OFF, we use rounds
        # to run the script a couple of times, right now it is set to 3.
        self.rounds = 0
    
    def execute(self):
        # schedule first round at time 0.
        self.schedule(0, self.__start_round)
        while self.events:
            t, _, callback = heapq.heappop(self.events)
            self.time_us = t
            # record before each event
            self.record_history()
            callback()
        self.log_f.close()
        # after simulation ends, plot the TEC history
        self.__make_plot()
        return

    def __log_state(self, node: CanNode):
        line = f"[STATE CHANGE] {node.name.upper()} -> {node.state.value} (TEC={node.TEC})"
        print(line)
        self.log_f.write(line + "\n")

    def __make_plot(self):
        """
        Plot the TEC history for attacker and defender.
        """
        plt.figure()
        plt.plot(self.history["time"], self.history["attacker"], marker='o', label="Attacker")
        plt.plot(self.history["time"], self.history["defender"], marker='s', label="Defender")
        plt.xlabel("Time (us)")
        plt.ylabel("Transmit Error Counter (TEC)")
        plt.title("TEC Evolution: Parrot Experiment 1")
        plt.legend()
        plt.grid(True)
        # save the plot to a file
        output_file = "plot_1.png"
        plt.savefig(output_file)
        print(f"Plot saved to {output_file}")

    # handle the round
    def __start_round(self):
        self.rounds += 1
        if self.rounds > MAX_ROUNDS:
            return
        self.log(f"=== ROUND {self.rounds} START ===")
        # initial simultaneous send
        self.log("Attacker sends spoofed frame", self.attacker)
        self.log("Defender sends D-frame", self.defender)
        self.schedule(0, self.__handle_collision)

    def __handle_collision(self):
        # collision snowball until error-passive
        self.attacker.collide()
        self.defender.collide()
        self.__log_state(self.attacker)
        self.__log_state(self.defender)
        if self.attacker.state == ErrorStates.ACTIVE:
            self.schedule(GAP_US, self.__handle_collision)
        else:
            self.schedule(GAP_US, self.__recover_defender)

    def __recover_defender(self):
        self.defender.succeed()
        self.log("Defender recovers send", self.defender)
        if self.defender.state != ErrorStates.ACTIVE:
            self.schedule(GAP_US, self.__recover_defender)
        else:
            self.__log_state(self.defender)
            self.schedule(GAP_US, self.__recover_attacker)

    def __recover_attacker(self):
        self.attacker.succeed()
        self.log("Attacker recovers send", self.attacker)
        if self.attacker.state != ErrorStates.ACTIVE:
            self.schedule(GAP_US, self.__recover_attacker)
        else:
            self.__log_state(self.attacker)
            self.schedule(GAP_US, self.__start_round)

# start the execution
if __name__ == "__main__":
    CanBus().execute()
