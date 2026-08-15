# Personas con identidad duplicada en el IGA — medido el 15-ago-2026

**Origen:** al diagnosticar los 409 `A patron record matching these details already exists`
de Koha se comprobó que no eran un fallo del conector: **Koha detecta duplicados por
apellidos + nombres + fecha de nacimiento**, y estaba impidiendo crear un segundo carné a
personas que ya tenían uno. La barrera funciona; lo que falla es que la misma persona
llega al IGA dos veces.

## Alcance

| | |
|---|---|
| **Personas con más de una identidad** | **136** |
| Identidades implicadas | 281 |
| Personas con 3 o más identidades | 8 |
| Personas con **más de un carné de Koha** | **0** |

Criterio: mismo `givenName` + `familyName` + `birthDate`, que es exactamente el que aplica Koha.

## Qué NO es el problema

- **No es el conector.** El 409 es la única barrera que impide duplicar carnés; si se sorteara,
  estas personas tendrían dos.
- **No son accesos indebidos.** De las identidades sin vínculo vivo, 33 ya están `DISABLED` y 11
  no tienen activación definida: ninguna está activa sin derecho.

## Los dos tipos

| Tipo | Pares | Naturaleza |
|---|---|---|
| **Mismo número, distinto relleno de ceros** | 6 | Artefacto técnico (`05436990` vs `005436990`) |
| **Identificadores realmente distintos** | ~72 | Dos fichas de negocio: típicamente una de estudiante y otra de trabajador |

El segundo grupo es el mismo defecto ya escalado como **544 fichas de persona duplicadas en
Oracle LAMB**. El IGA las refleja fielmente: son dos fichas en el origen, luego dos identidades.

## Por qué no se corrige desde aquí

Fusionar identidades exige decidir, por persona, **cuál sobrevive** y qué ocurre con sus accesos,
su correo institucional y su historial de préstamos. Es una decisión de negocio con impacto en
personas reales, no una limpieza técnica. Se documenta para llevarla a RRHH y a los DBAs de LAMB.

## Listado

`nombre;fecha_nac;idA;afiliacionA;activacionA;carnetsA;idB;afiliacionB;activacionB;carnetsB`

```
Abraham Daniel Amaro Leal;1990-03-13;002922070;staff;ENABLED;0;001261927;staff;ENABLED;0
Abraham Daniel Amaro Leal;1990-03-13;02922070;staff;ENABLED;0;001261927;staff;ENABLED;0
Abraham Daniel Amaro Leal;1990-03-13;02922070;staff;ENABLED;0;002922070;staff;ENABLED;0
Adiel Ernesto Mamani Surco;1996-09-18;04731168;staff;ENABLED;0;001283770;staff;DISABLED;0
Adrian Alberto Pereira Pinzon;1992-03-05;02289427;SIN VINCULO;DISABLED;0;06158248;staff;ENABLED;1
Albert Caleb Tacilla Vargas;1999-07-10;71218915;staff;DISABLED;0;201611709;student;ENABLED;1
Albert Jose Bermudez Lopez;1996-09-20;14639216;SIN VINCULO;DISABLED;0;03412246;SIN VINCULO;DISABLED;0
Alessandra Marques Sohn;1987-07-25;201611865;alum;ENABLED;0;01595402;staff;ENABLED;0
ALEXANDER JAVIER LEAL SULBARAN;1994-03-20;734472371;staff;DISABLED;0;002508232;staff;ENABLED;0
Alexander Rafael Morillo Campos;1992-02-29;201912967;student;ENABLED;1;02610996;staff;DISABLED;0
Ana Cristina Velasquez Calvo;1998-11-21;06645032;SIN VINCULO;DISABLED;0;006645032;faculty;ENABLED;1
Ana Virginia Araujo Briceño;1983-12-30;7982041171;staff;ENABLED;0;002505363;staff;DISABLED;0
Anderson Gustavo Chanaluisa Taipe;2003-12-30;005994373;SIN VINCULO;DISABLED;1;05994373;staff;DISABLED;0
Anderson Gustavo Chanaluisa Taipe;2003-12-30;202212353;student;-;0;005994373;SIN VINCULO;DISABLED;1
Anderson Gustavo Chanaluisa Taipe;2003-12-30;202212353;student;-;0;05994373;staff;DISABLED;0
Anderson Nelver Elías Soriano Moreno;1995-11-19;201320450;alum;-;0;71850479;SIN VINCULO;DISABLED;0
Andrea Estefania Inca Portilla;1990-02-24;201120601;alum;ENABLED;0;001138475;staff;ENABLED;0
Angelica Elizabeth Gualli Yantalema;2004-07-04;06182214;staff;DISABLED;0;202313191;student;ENABLED;1
Angelica Maria Figueroa Garay;1981-09-04;202521482;SIN VINCULO;-;0;9910456;alum;-;0
ARIANA ALESSANDRA YANCE CCESA;2008-08-10;323200401;SIN VINCULO;-;1;202613758;student;ENABLED;0
Aurelia ULLOA HUAMASH;1975-06-16;15861951;staff;ENABLED;0;9610175;alum;ENABLED;1
Beatriz Marlene Tello Pulido;1978-02-10;22521444;staff;ENABLED;0;7982041277;staff;ENABLED;0
Brandon Elcana Armijos Bravo;1998-11-06;007705414;staff;DISABLED;0;202311193;student;ENABLED;1
Brayan Sebastian Vargas Patiño;1996-11-30;201820260;student;ENABLED;1;01794074;SIN VINCULO;DISABLED;0
Brita Soledad Masco Ccama;1990-12-01;202321158;alum;-;1;200810325;alum;-;0
Candy Isabel Jordan Chirino;1991-04-22;201810626;SIN VINCULO;DISABLED;1;01794507;SIN VINCULO;DISABLED;0
Carlos Huacal Fernandez;1965-07-25;16639130;staff;ENABLED;0;8610187;alum;-;0
Carlos Javier Carmona Bello;1979-04-11;03012465;SIN VINCULO;DISABLED;0;003012465;faculty;ENABLED;1
Carlos Juaquin Rivas Mendez;1971-03-05;41073385;staff;ENABLED;0;200110183;alum;-;0
Carmen Felícita Espinoza Córdova;1975-07-06;200820099;alum;-;0;21135534;staff;DISABLED;0
Carmen Palomino Guevara;1975-07-17;43261126;staff;ENABLED;0;9220060;alum;-;0
Christian Brandal Ødegård;1996-05-24;007736542;SIN VINCULO;DISABLED;0;202412677;SIN VINCULO;-;1
Cindy Vanessa Montoya Guevara;1991-05-14;201410213;alum;-;0;01076311;staff;DISABLED;0
Claudia Maribel Cueva Benavides;1992-12-14;201010330;alum;ENABLED;0;00103712;SIN VINCULO;DISABLED;0
Corpus Garcia Valdez;1987-08-10;200910348;alum;-;0;44425789;staff;ENABLED;0
Cristhian Josue Chamba Sanchez;2005-06-14;202410268;student;-;1;07591353;staff;DISABLED;0
Damaris Gelvez Chanaga;1988-07-23;00188782;staff;ENABLED;0;612505;staff;ENABLED;0
DANIELA GOMEZ SOTO;1989-07-27;49102219;staff;ENABLED;0;005164536;staff;ENABLED;0
Danilo Rafael Suarez Salgado;1970-05-13;02791802;staff;DISABLED;0;803487908;staff;DISABLED;0
David Angel Quispe Suna;2004-01-31;77915883;staff;ENABLED;0;202210614;student;ENABLED;1
David Remberto Sarzuri Marin;1966-12-20;001592668;SIN VINCULO;DISABLED;0;201910859;alum;ENABLED;0
Dayana Iveth Morales Paredes;1999-10-30;005705811;staff;ENABLED;1;202122320;alum;ENABLED;0
Dilan Deyvi Castro Chacon;2002-05-15;612483570;staff;DISABLED;0;201910238;alum;ENABLED;0
Dina Angulo Pereyra;1969-11-27;8710054;alum;-;0;23003510;staff;DISABLED;0
Edith Milagros Plasencia Salas;1998-08-11;324111605;SIN VINCULO;-;0;324111581;SIN VINCULO;-;1
Edwin Choque Sucapuca;1981-11-16;200010210;alum;-;0;42469849;staff;ENABLED;0
Eleazar Santiago Huiñac Castillejo;1963-02-21;05390062;staff;ENABLED;0;9310041;alum;-;0
Eliana Berrios Macedonio;1983-05-14;202614829;SIN VINCULO;DISABLED;1;01122288;staff;ENABLED;0
Eliseo Sanchez Chavez;1949-09-26;9520113;alum;-;0;00016576;staff;ENABLED;0
Elvigia Beltran Avellaneda;1963-03-14;07882780;staff;ENABLED;0;201820371;alum;-;0
Elvis Salas Leqque;1989-02-21;202614730;SIN VINCULO;DISABLED;1;45550632;staff;ENABLED;0
Enmanuel José Albarran Castillo;2001-11-17;07134778;staff;ENABLED;1;202211499;SIN VINCULO;DISABLED;0
Erika Nunes Da Silva;2002-03-04;324111549;student;-;1;07451681;staff;DISABLED;0
Evelyn del Valle Marin Hernandez;1989-12-14;01056037;staff;ENABLED;1;131294400;SIN VINCULO;DISABLED;0
Fabiola Mecedes Melgar Vaca;1991-03-05;734472422;staff;DISABLED;0;202521325;SIN VINCULO;-;0
Fabiola Mecedes Melgar Vaca;1991-03-05;734472422;staff;DISABLED;0;002295311;staff;ENABLED;0
Fabiola Mecedes Melgar Vaca;1991-03-05;002295311;staff;ENABLED;0;202521325;SIN VINCULO;-;0
Falvia Sugey Paradas xx;1974-10-11;772452072;staff;DISABLED;0;006617184;staff;ENABLED;0
Felix Manuel Lopez Pedrozo;2007-06-18;001914761;SIN VINCULO;DISABLED;1;202511206;student;ENABLED;0
Fiorella Violeta Ferreyra Castillo;1959-02-26;200211178;alum;-;0;07948406;staff;ENABLED;0
Gilda Sapillado Condori;1991-08-26;200920486;faculty;ENABLED;1;201810596;faculty;ENABLED;0
Giovanna Isolina Grijalva Fuentes;1975-08-26;07502908;staff;DISABLED;0;7502908;staff;DISABLED;0
Grecia Mayerlin Melendez Luna;1989-08-11;004229142;staff;ENABLED;0;89008225;staff;ENABLED;0
Ibony Cutisaca Mamani;1986-09-30;43919809;SIN VINCULO;DISABLED;0;200410450;alum;-;0
Indira Raquel Gutierrez Jove;2003-05-22;202013708;student;ENABLED;1;75949654;staff;DISABLED;0
Isidoro Rodriguez Vilca;1960-12-14;02408680;staff;ENABLED;0;200710630;alum;-;0
Itler Miguel Asto Quillahuaman;1983-08-25;41944685;staff;ENABLED;0;200210072;staff;ENABLED;1
Ivan Jose Pierantozzi Fuchs;1990-05-02;02421367;staff;DISABLED;0;717218662;SIN VINCULO;DISABLED;0
Jacksaint Saintila;1986-04-04;201020351;alum;-;0;000837035;faculty;ENABLED;1
Jairo Carloman Ocupa Julca;1994-07-31;201812397;alum;ENABLED;0;48418316;staff;ENABLED;0
JANKARY NAISVELIN MORENO ESCOBAR;1997-04-03;806702063;staff;ENABLED;0;007129983;staff;ENABLED;0
Jeff Asael Brañez Medrano;1992-05-18;200920277;alum;-;0;73114873;staff;DISABLED;0
Jeshiel Del Pilar Gomez Gomez;1992-01-22;003656108;staff;ENABLED;0;772452024;staff;ENABLED;0
Jesus Armando Diaz Sanchez;1998-05-13;71760258;staff;ENABLED;0;201612553;staff;ENABLED;1
Jhonney Eduardo Romero Cuica;1991-06-17;00066766;staff;ENABLED;1;02095296;staff;DISABLED;0
Jhonny De Jesus Romero Cuica;1988-05-01;003720368;staff;ENABLED;0;89008228;staff;ENABLED;0
Jhonny De Jesus Romero Cuica;1988-05-01;003720368;staff;ENABLED;0;005830760;staff;ENABLED;0
JHONNY DE JESUS ROMERO CUICA;1988-05-01;89008228;staff;ENABLED;0;005830760;staff;ENABLED;0
Jinesska Yoliset Rangel Nava;1983-02-18;49094066;staff;ENABLED;0;03542851;staff;ENABLED;0
Jordan Ariel Castillo Marquez;2002-07-25;202412586;SIN VINCULO;-;1;009010298;staff;DISABLED;0
Jose Gregorio Moreno Brito;1970-11-29;02504832;SIN VINCULO;DISABLED;0;03516478;staff;DISABLED;0
Jose Gregorio Moreno Brito;1970-11-29;02507832;staff;ENABLED;1;02504832;SIN VINCULO;DISABLED;0
Jose Gregorio Moreno Brito;1970-11-29;02507832;staff;ENABLED;1;03516478;staff;DISABLED;0
Joselyn Stefanny Tambi Tabango;2001-06-21;06328442;staff;DISABLED;0;202117740;alum;-;1
Jose Miguel Casique Rodriguez;1993-04-23;02010246;staff;ENABLED;0;00210544;staff;ENABLED;0
Juan Elvis Salazar Varon;1979-07-29;40474107;staff;ENABLED;0;201012183;alum;-;0
Jucimeire Nascimento De Morais;1980-01-28;009521766;staff;ENABLED;0;000886095;staff;ENABLED;0
Ken Jefrey Nieto Flores;1992-03-24;03657510;staff;ENABLED;1;202212637;student;ENABLED;0
Kerlly Viviana Yanzapanta Cruz;1993-06-19;00956824;staff;DISABLED;0;201310057;alum;ENABLED;0
Kerly Micaela Cuyachamin Oña;2003-05-19;202311064;student;ENABLED;1;009006913;staff;DISABLED;0
Kleyder Eduardo Narro Plasencia;1992-11-21;7232579;staff;ENABLED;0;201010254;alum;-;0
Laura De Alcantara Barros;2000-10-27;05868861;staff;DISABLED;0;202410412;student;-;1
Leidy Carolina Gomez Traslaviña;1989-06-26;202120384;alum;-;0;01247350;staff;ENABLED;0
Leila Joerlin Salcedo Vargas;1987-05-21;003319040;staff;ENABLED;0;97852560;staff;ENABLED;0
Lesly Konny Guaman Macas;2003-08-04;006256305;SIN VINCULO;DISABLED;0;06256305;staff;DISABLED;0
Lesly Konny Guaman Macas;2003-08-04;006256305;SIN VINCULO;DISABLED;0;202212611;student;-;1
Lesly Konny Guaman Macas;2003-08-04;202212611;student;-;1;06256305;staff;DISABLED;0
Liberata Taco Mollo;1974-12-21;200311495;alum;-;0;202421197;faculty;ENABLED;1
Lilia Graciela Zarate Ospinal;1958-09-29;09307240;SIN VINCULO;DISABLED;0;200611600;alum;-;0
Lisle Jahely Juarez Serquen;2000-07-22;201811693;staff;ENABLED;1;75609890;staff;ENABLED;0
Lizeth Rojas Silva;1985-12-24;201320421;alum;ENABLED;0;73389823;staff;ENABLED;0
Llerlis Darlyne Marin Soria;2008-09-19;324104478;SIN VINCULO;-;1;324100835;SIN VINCULO;-;0
Lucilene Da Cruz Lima Britis;1971-06-18;07158945;staff;DISABLED;0;00466826;staff;ENABLED;0
Luis Fernando Suarez López;2003-11-27;006431780;staff;ENABLED;0;202212641;student;ENABLED;1
Luis Trinidad Laurencio;1971-01-07;9220052;alum;-;0;04307378;staff;ENABLED;0
Mabel Quintana Sanchez;1983-09-28;42128354;staff;ENABLED;0;200810048;alum;-;0
Manuel Roy Vaca Espino;1961-11-21;9920030;alum;-;0;09118525;staff;ENABLED;0
MARIA ELENA(Hija DeJOSE) HUAMAN OBANDO;1974-03-24;4519;staff;ENABLED;0;18183475;staff;ENABLED;0
MARIA ESTHER VALDIVIA CAMPOS;1985-05-24;42979928;staff;DISABLED;0;72979928;staff;ENABLED;0
Maribel Mamani Rodriguez;1991-12-05;201420937;alum;-;0;201913034;alum;-;1
Marly Johana Trigos Gelvez;1996-09-14;201911193;alum;ENABLED;0;01646638;staff;DISABLED;0
Martha Leonor Vergara Flores;1983-10-08;45073116;staff;ENABLED;0;7982041271;staff;ENABLED;0
Martín David Castillo Ariza;1996-10-11;201611871;alum;ENABLED;1;01419882;staff;DISABLED;0
Mayerlin Mishell Mora Ruiz;2005-08-29;202412585;student;-;0;007740968;SIN VINCULO;DISABLED;1
Medalit Alvarado Santos;2000-03-08;202310475;student;ENABLED;1;72649990;staff;DISABLED;0
Michael Christian Orellana Mendez;1978-09-04;9610006;alum;-;0;40667583;faculty;DISABLED;0
Moises Antonio Villavicencio Baez;1974-11-30;2006115411;student;ENABLED;1;25794864;staff;ENABLED;0
Natalia Raquel Benavides Paredes;1999-12-01;002558245;SIN VINCULO;DISABLED;0;201810090;alum;ENABLED;0
Nathalia Jhoana Chaparro López;1994-03-18;01006524;staff;DISABLED;0;201320459;faculty;ENABLED;1
Nayeli Raquel Catacora Castro;2002-04-12;006132492;staff;ENABLED;1;202100603;alum;-;0
Odalys Coromoto Velasquez Gomez;1960-06-15;000274925;staff;ENABLED;0;006505635;staff;DISABLED;0
Orlando Carlos Segura Torres;1973-07-06;9210342;alum;ENABLED;0;03229920;staff;ENABLED;0
Oscar Antonio Lozano Ventura;1990-12-08;46740050;staff;DISABLED;0;72500488;staff;ENABLED;0
Osclaris Jhoanna Martinez Avila;2000-10-23;201711673;alum;ENABLED;0;01660870;staff;ENABLED;1
Paúl Eduardo Villao Mendoza;1992-03-28;201410400;student;-;0;001502765;SIN VINCULO;DISABLED;1
Rafaela Barros De Figueiredo;1996-05-31;01581490;staff;DISABLED;0;201711826;alum;ENABLED;0
Reyna Esther Ponce Salazar;2008-01-07;202610583;student;ENABLED;1;324104230;SIN VINCULO;-;0
Rodolfo Samuel Velasquez Bermeo;1992-11-23;201910777;alum;ENABLED;0;004719477;staff;DISABLED;0
Rosa Angélica Salazar Paredes;1994-10-04;201210205;alum;-;0;74126636;staff;ENABLED;0
Ruth Yesenia De Los Santos Saldaña;1995-05-12;201410375;alum;-;0;76622857;SIN VINCULO;DISABLED;0
Ruthy Mamani Jacinto;1989-12-05;202320885;faculty;ENABLED;1;05436990;staff;ENABLED;0
Sara Manco Gomez;1996-06-24;02288622;staff;DISABLED;0;201910860;alum;ENABLED;1
Seyei Rengifo Arévalo;1998-02-16;94703250;SIN VINCULO;DISABLED;0;201522222;faculty;ENABLED;1
Shessira Stheisy Quispe Rodriguez;1995-12-12;771245544;staff;DISABLED;0;201221992;student;ENABLED;1
Stephania Domenica Gonzalez Delgado;2002-02-20;201911406;alum;ENABLED;0;02415907;staff;DISABLED;0
Tania Paulina Zhunaula Guaman;1993-09-09;201220141;alum;-;0;001265190;staff;DISABLED;0
Vania Stephany Sarzuri Cuellar;1998-07-19;01677740;staff;ENABLED;0;06405799;staff;ENABLED;0
Vania Stephany Sarzuri Cuellar;1998-07-19;01677740;staff;ENABLED;0;201612863;alum;ENABLED;1
Vania Stephany Sarzuri Cuellar;1998-07-19;06405799;staff;ENABLED;0;201612863;alum;ENABLED;1
Vania Stephany Sarzuri Cuellar;1998-07-19;00167774;staff;ENABLED;0;01677740;staff;ENABLED;0
Vania Stephany Sarzuri Cuellar;1998-07-19;00167774;staff;ENABLED;0;06405799;staff;ENABLED;0
Vania Stephany Sarzuri Cuellar;1998-07-19;00167774;staff;ENABLED;0;201612863;alum;ENABLED;1
Veronica Vasquez Burga;1991-12-27;70160338;staff;DISABLED;0;63040203;SIN VINCULO;DISABLED;0
Walter Ernesto Cabrera Magariño;1978-03-22;9710074;alum;-;0;07530434;staff;ENABLED;0
Wendy Chuquimia León;1988-04-08;202321005;alum;ENABLED;1;200410812;alum;-;0
Wilson Renan Umaquinga Lanchimba;1996-12-06;201611743;alum;ENABLED;0;05880971;staff;DISABLED;0
YAHIR ALEXANDER NEIRA CURO;2007-12-27;324110503;SIN VINCULO;DISABLED;1;202623077;SIN VINCULO;-;0
Yelangelis Del Valle Rodriguez Ramirez;1989-12-08;001558195;staff;ENABLED;0;01558195;SIN VINCULO;DISABLED;0
Yelangelis del Valle Rodriguez Ramírez;1989-12-08;49101799;SIN VINCULO;DISABLED;0;001558195;staff;ENABLED;0
Yelangelis del Valle Rodriguez Ramírez;1989-12-08;49101799;SIN VINCULO;DISABLED;0;01558195;SIN VINCULO;DISABLED;0
Yesica Marleni Pulluyqueri Ito;1988-04-08;45552979;staff;DISABLED;0;200511154;alum;-;0
Yudhy Mamani Chambi;1971-10-06;8910194;alum;-;0;02428075;staff;ENABLED;0
Yunier Valderrama Falero;1983-01-30;007769582;SIN VINCULO;DISABLED;0;07769582;staff;DISABLED;0
```
