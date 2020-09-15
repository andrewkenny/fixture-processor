This folder contains the code and assets for the fixture modifier program.

This program is intended to do the following:
(in order of percieved difficulty)

 - Remove wires from the wires file. (and eventually from the fixture file)

    this would simplify the programming instructions.


 - Add extra wiring to the wires file. (and eventually the fixture)
   This would include:

    1, connections on the otherside of single defined GP relays
    2, Power supplies with a reference other than ground.
    3, Similar to 1 and 2, power supplies via GP relays.
    4, if we can work out a method of doing so - providing an easy way to add wires with 2 pin comonents (eg resistors)

 - add dummy transfers to the wires file, inserts file. (and eventually the fixture file)
   in conjunction with the first 2 modes, this would (in theory) allow:

    1, Automatic wiring and verifier testing of mux card wiring to custom transfer / ribbon cable connector.
    2, Automatic wiring and verifier testing of Testjet from mux card to amp board recepticle.
    3, Automatic wiring of pre-defined relay cards.
    4, Automatic wiring of pre-defined custom routed circuit boards.
    5, Automatic wiring of CMM cards (if a well defined method of holding them was developed.)

 - Useful information:
    1, increasing the BRC column by 1 decreases the X value by 1500. (in module 2)
	2, increasing the BRC row by 1 hole increases the y value by 7000. (in module 2)
	
	3, For a bank 2 / full bank fixture.
       20101 is: 135111  -81725
	   20178 is:  19611  -81725
	   22301 is: 135111   72275
       22378 is:  19611   72275


       10101 is: 277611  -81725
	   10178 is: 162111  -81725
	   12301 is: 277611   72275
       12378 is: 162111   72275

       For a bank 1 only fixture.
       12301 is: 135111   72275
       12378 is:  19611   72275
       10178 is:  19611  -81725
       10101 is: 135111  -81725
       
       
       


    

      