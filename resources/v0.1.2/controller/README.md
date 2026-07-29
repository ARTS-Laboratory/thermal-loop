# Controller Code

* The LabVIEW Controller code
* **LabVIEW\_SMR\_V1:**  
* 
* First iteration of the LabVIEW for the thermal loop, completed 6/24/26.  
* 
* Only goals of this was to confirm that values are being read from the heat exchanger, all 7 pressure transducers, and all 8 thermocouples.  
* 
* Problems to fix:  
* 
* Incorrect flow meter value (around 0.2 GPM too high) 
* 
* Incorrect P4 measurement, as well as possibly others incorrect as well 
* 
* Temp. And Pressure graphs not reading history of each different sensor, instead combining them into one function 
* 
* No labels on the array of outputs 
* 
* To be added in future iterations:  
* 
* proportional valve showing and PID control established 
* 
* Possibly flow meter in main loop wired to show readings as well (will need to investigate further to see about buying a new one or if able to wire to current) 
* 
* &#x20;
* 
* **LabVIEW\_SMR\_V2:**  
* 
* Focused on fixing problems from first iteration: 
* 
* Pressure not reading correctly (deep dive into P4 wiring still required, possibly not a LabVIEW problem) 
* 
* Graphs fixed 
* 
* Compensator attempted to be added to fix incorrect flowmeter output, although needs to be fine tuned (possibly with a function?) 
* 
* Arrays fixed so that labels for data points are visible 

