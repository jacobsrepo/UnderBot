# Hardware interfaces

This document retains the useful system boundaries from the retired electrical
and PCB drafts. It is not a wiring diagram or authorization to energize hardware.

## Confirmed direction

- The computer target is a Raspberry Pi running Linux.
- STM32 is the selected microcontroller family for the future low-level adapter;
  the exact board, pins, firmware, and electrical interface are unresolved.
- The Xiaomi T12 base should initially retain its original battery, charging
  system, and controller. Its command, feedback, LiDAR, battery-sense, and stop
  interfaces have not been established.
- Arm and gripper commands must respect the selected arm controller rather than
  assuming direct PWM. Exact actuator models, voltage, protocol, current, zero,
  direction, and measured limits must be confirmed on the physical assembly.
- Raspberry Pi, MCU, sensors, and actuators need a common, documented grounding
  and power strategy unless a selected interface is galvanically isolated.

## Required controller contract

The Pi-side adapter should send versioned, bounded commands with sequence IDs and
deadlines. The controller must acknowledge accepted targets and return measured
state, faults, and stop status. Reconnection must start stopped and must never
resume an old motion automatically.

The MCU or retained motor controller must enforce local limits and stop when its
command deadline expires, even if the Pi, network, ROS node, or AI process fails.
A physical stop input and controller power behavior must be verified separately;
a chat or software stop is not an emergency-stop circuit.

## Decisions required before powered integration

1. Record exact labels and connectors for the T12, its battery, motors, LiDAR,
   dock, and internal controller.
2. Identify the exact STM32 board and logic voltage.
3. Identify each arm/gripper actuator and its controller, supply range, peak
   current, feedback type, and communication protocol.
4. Measure joint direction, zero, safe limits, response time, and unloaded current
   one joint at a time with the mechanism supported.
5. Define the stop path, watchdog, fusing, branch wiring, and behavior on loss of
   arm power before enabling autonomous motion.
6. Implement one shared software command/state interface with Gazebo and hardware
   adapters, then compare small simulated and physical movements.

Commercial protected power modules and harnesses are sufficient for prototyping;
this project does not plan to design or manufacture a custom PCB.
