This folder contains the work of Chris Heaps on simulations of the SMR loop in Simscape. Versions are detailed as follows:

v1.0.1: First working model, uses constant energy supply to the fuel rod and constant city side water supply temperature

v1.0.2: Adds transient initial conditions for the loop. This includes a function to represent slight variations in the city water supply temperature. Also adds a direct voltage input for the heat supplied to the simulated fuel rod, just as the actual loop has.

v1.0.3: Retains the same features as previous model and adds controllable power supply for varying voltages. This is the most stable and accurate version of the model so far. Longest test has been twelve hours and it maintained the cutoff temperature almost perfectly throughout the main loop for the entire test.

Next versions: Redesign for incorporation with SpeedGoat real time target computer.