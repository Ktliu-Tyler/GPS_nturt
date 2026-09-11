# GPS-to-CAN Telemetry for NTU Racing

A lightweight Python project that transfers GPS receiver data onto a vehicle CAN bus. It reads NMEA sentences from a serial-connected receiver, extracts position and motion information, and packs those values into CAN frames for other vehicle electronics or logging tools.

## Purpose

GPS receivers and vehicle control systems often use different interfaces. This project provides the bridge between serial GPS output and CAN-based telemetry, with diagnostic tools for checking the receiver and a service-oriented deployment structure for a Raspberry Pi.

## Main components

- Serial reception and NMEA parsing.
- CAN messages for latitude/longitude, altitude, and velocity components.
- A direct Python sender that does not require a ROS 2 node.
- Receiver tests, baud-rate discovery, raw-data inspection, and frequency diagnostics.
- Shell scripts and a systemd service definition for deployment.

| Path | Role |
| --- | --- |
| [gps_can_sender.py](gps_can_sender.py) | NMEA-to-CAN conversion and transmission |
| [gps_test.py](gps_test.py) | Receiver checks and raw serial inspection |
| [gps_diagnostic.py](gps_diagnostic.py) | GPS output-rate diagnostics |
| [gps_decoder.py](gps_decoder.py) | Additional GPS decoding and inspection |
| [analyze_gps_output.py](analyze_gps_output.py) | GPS output analysis |
| [SERVICE_README.md](SERVICE_README.md) | Existing service deployment and operation notes |

## Technical approach

The sender uses `pyserial`, `pynmea2`, and `python-can`. Its default configuration targets a Linux serial device and a SocketCAN interface. Frame identifiers and packing rules are defined in the sender itself, so the receiving decoder must use the same schema.

## Project context

This is the direct serial-to-CAN branch of the GPS work in this project collection. [GPS_tracker](https://github.com/Ktliu-Tyler/GPS_tracker) preserves the broader ROS 2-based experiments, logging, visualization, and alternative encodings. Their CAN formats should be compared explicitly rather than assumed to be interchangeable.
