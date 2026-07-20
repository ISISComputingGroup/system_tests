## configure galil crate 5

## passed parameters
##   GCID - galil crate software index. Numbering starts at 0 - will always be 0 if there is one to one galil crate <-> galil IOC mapping
##   GALILADDR - address of this galil

## see README_galil_cmd.txt for usage of commands below

GalilCreateController("Galil", "$(GALILADDR=127.0.0.1)", -40)

GalilCreateAxis("Galil","A",0,"",1)
GalilCreateAxis("Galil","B",0,"",1)
GalilCreateAxis("Galil","C",0,"",1)
GalilCreateAxis("Galil","D",0,"",1)
GalilCreateAxis("Galil","E",0,"",1)
GalilCreateAxis("Galil","F",1,"",1)
GalilCreateAxis("Galil","G",1,"",1)
GalilCreateAxis("Galil","H",1,"",1)

GalilStartController("Galil","$(GALIL)/gmc/galil_Default_Header.gmc;$(GALIL)/gmc/galil_Home_Home+FIneg.gmc!$(GALIL)/gmc/galil_Home_Home+FIpos.gmc!$(GALIL)/gmc/galil_Home_Home+FIneg.gmc!$(GALIL)/gmc/galil_Home_Home+FIneg.gmc!$(GALIL)/gmc/galil_Home_Home+FIneg.gmc!$(GALIL)/gmc/galil_Home_RevLimit.gmc!$(GALIL)/gmc/galil_Home_RevLimit.gmc!$(GALIL)/gmc/galil_Home_Home.gmc;$(GALIL)/gmc/galil_Default_Footer.gmc",0,0,3)
