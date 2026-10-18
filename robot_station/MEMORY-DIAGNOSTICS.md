# PostgreSQL memory investigation — 2026-10-03

The application uses the private PostgreSQL instance on 127.0.0.1:55432.
The stopped Windows service named postgresql-x64-18 is a different instance;
starting that service is not the remedy for this application.

Direct read-only lookup and the running gateway both returned enrolled people
during investigation. The previously reported failure was not reproduced.
One standalone helper lookup took 5.64 seconds against the old 8-second limit;
this suggests a possible timeout under load, but does not prove its cause.

Changes deployed with backups to D:/Robotics/robot-station:

- Increased helper process timeout to 20 seconds. Database connection and
  statement timeouts remain bounded at 3 seconds.
- Distinguished helper timeout, nonzero exit, malformed response and database
  exception type. Logs omit raw exception messages and connection credentials.
- Identity replies explain timeout instead of reporting a generic outage.
- Fixed the installed open-station.ps1 launcher to retain the AI endpoint,
  memory interpreter and memory configuration when starting a fresh station.
  The portable repository launcher remains separately configurable.

The local station bridge/gateway was restarted; database and camera processes
were left running. Foxglove clients reconnected. Thirty unit tests passed in the
ROS environment. Live chat checks cover known and unknown identities, proposed
plans with execution disabled, and a Qwen answer grounded in supplied memory.

This memory helper reads the enrolled-people gallery; it does not provide
general conversation history, biographies or current locations.

If the failure recurs, inspect demo-errors.log for `Memory lookup unavailable`
and its error code. Use the existing Start UnderBot Base.cmd if the private
database has not been started following a shutdown. No Windows boot autostart
was added by this repair.
