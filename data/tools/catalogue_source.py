"""Source table for data/catalogue.csv.

One line per SKU, fields separated by ';':
key;brand;strength;form;pack;molecule;group;unit;aliases

`key` is an internal handle used by the generator to reference SKUs (inbox
ground truth, decoy logic). It is not written to the CSV. Aliases are
pipe-separated, lower case, and cover how chemists say and write the item.
Capsules are classed as form "tablet" because the contract has no capsule form.
"""

CATALOGUE_TEXT = """
dolo650;Dolo 650;650 mg;tablet;15 tablets;Paracetamol;fever;strip;dolo|dolo 650|dolo650|dolo sau pachas|dolo chhe sau pachas|dolo 650 mg|dollo|dolo six fifty
dolo500;Dolo 500;500 mg;tablet;15 tablets;Paracetamol;fever;strip;dolo 500|dolo500|dolo paanch sau|dolo 500mg
dolo120;Dolo 120 Suspension;120 mg/5 ml;syrup;60 ml;Paracetamol;fever;bottle;dolo 120|dolo syrup|dolo suspension|dolo bachchon wali|dolo syp
dolo250;Dolo 250 Suspension;250 mg/5 ml;syrup;60 ml;Paracetamol;fever;bottle;dolo 250|dolo 250 syrup|dolo 250 syp|dolo dhai sau
crocinadv500;Crocin Advance;500 mg;tablet;15 tablets;Paracetamol;fever;strip;crocin|crocin advance|crocin 500|crocin adv|crosin|crocin paanch sau
crocin650;Crocin 650;650 mg;tablet;15 tablets;Paracetamol;fever;strip;crocin 650|crocin650|crosin 650|crocin chhe sau pachas
crocinds;Crocin DS Suspension;250 mg/5 ml;syrup;60 ml;Paracetamol;fever;bottle;crocin ds|crocin syrup|crocin suspension|crocin syp|crocin bachchon wali
calpol500;Calpol 500;500 mg;tablet;15 tablets;Paracetamol;fever;strip;calpol|calpol 500|calpol500|kalpol|calpol paanch sau
calpol650;Calpol 650;650 mg;tablet;15 tablets;Paracetamol;fever;strip;calpol 650|calpol650|kalpol 650
calpol120;Calpol 120 Suspension;120 mg/5 ml;syrup;60 ml;Paracetamol;fever;bottle;calpol 120|calpol syrup|calpol syp|calpol suspension|calpol bachchon wali|calpol drops
calpol250;Calpol 250 Suspension;250 mg/5 ml;syrup;60 ml;Paracetamol;fever;bottle;calpol 250|calpol 250 syrup|calpol 250 syp
pacimol650;Pacimol 650;650 mg;tablet;15 tablets;Paracetamol;fever;strip;pacimol|pacimol 650|pacimol650|pasimol 650|pacimol chhe sau pachas
pacimol500;Pacimol 500;500 mg;tablet;10 tablets;Paracetamol;fever;strip;pacimol 500|pacimol500|pasimol 500
paracip500;Paracip 500;500 mg;tablet;10 tablets;Paracetamol;fever;strip;paracip|paracip 500|paracip500|parasip
pcm500;Paracetamol IP (generic);500 mg;tablet;10 tablets;Paracetamol;fever;strip;pcm|pcm 500|pcm500|paracetamol|paracetamol 500|para 500|p c m|paracetamol tablet
combiflam;Combiflam;400 mg + 325 mg;tablet;20 tablets;Ibuprofen + Paracetamol;fever;strip;combiflam|combi flam|combiflame|combiflam tablet|combi
brufen400;Brufen 400;400 mg;tablet;15 tablets;Ibuprofen;fever;strip;brufen|brufen 400|brufin|brufen400|ibuprofen 400
ibugesicplus;Ibugesic Plus Suspension;100 mg + 162.5 mg/5 ml;syrup;60 ml;Ibuprofen + Paracetamol;fever;bottle;ibugesic plus|ibugesic|ibugesic syrup|ibugesic plus syp|ibugesic bachchon wali
meftalp;Meftal-P Suspension;50 mg + 125 mg/5 ml;syrup;60 ml;Mefenamic Acid + Paracetamol;fever;bottle;meftal p|meftal-p|meftal p syp|meftal p syrup|meftalp|meftal p drops|meftal pee
sumo;Sumo;100 mg + 325 mg;tablet;10 tablets;Nimesulide + Paracetamol;fever;strip;sumo|sumo tablet|sumo tab|sumo nimesulide
ors;ORS Sachet (WHO formula);21.8 g;sachet;1 sachet;Oral Rehydration Salts;diarrhoea;sachet;ors|o r s|o.r.s.|ors packet|ors sachet|ors powder|ors ka packet|ors who|oral rehydration
electral;Electral Powder;21.8 g;sachet;1 sachet;Oral Rehydration Salts;diarrhoea;sachet;electral|electrol|electral powder|electrall|ilectral|electral ors|electral packet|electral sachet
norfloxtz;Norflox-TZ;400 mg + 600 mg;tablet;10 tablets;Norfloxacin + Tinidazole;diarrhoea;strip;norflox tz|norflox-tz|norfloxtz|norflok tz|norflox tej|noroflox tz|nor tz|norflox t z|norflox tez
norflox400;Norflox 400;400 mg;tablet;10 tablets;Norfloxacin;diarrhoea;strip;norflox|norflox 400|norflox400|norfloxacin|noroflox 400
ofloxoz;Oflox-OZ;200 mg + 500 mg;tablet;10 tablets;Ofloxacin + Ornidazole;diarrhoea;strip;oflox oz|oflox-oz|ofloxoz|oflox o z|oflox oj|oflox
ciploxtz;Ciplox-TZ;500 mg + 600 mg;tablet;10 tablets;Ciprofloxacin + Tinidazole;diarrhoea;strip;ciplox tz|ciplox-tz|cipro tz|ciproflox tz|siplox tz
ondem4;Ondem 4;4 mg;tablet;10 tablets;Ondansetron;diarrhoea;strip;ondem|ondem 4|ondem4|ondem four|ondem char|ondem 4mg|ondam|ondem chaar|ondansetron 4|ondem ke 4
ondemsyr;Ondem Syrup;2 mg/5 ml;syrup;30 ml;Ondansetron;diarrhoea;bottle;ondem syrup|ondem syp|ondem 2 mg syrup|ondem bachchon wali|ondem drops
emeset4;Emeset 4;4 mg;tablet;10 tablets;Ondansetron;diarrhoea;strip;emeset|emeset 4|emiset|emeset4|emesett
redotil100;Redotil 100;100 mg;tablet;10 capsules;Racecadotril;diarrhoea;strip;redotil|redotil 100|racecadotril|racecadotril 100|resecadotril|redotil sau|racecadotril capsule|redotill
racecadotril10;Redotil 10 Sachet;10 mg;sachet;10 sachets;Racecadotril;diarrhoea;sachet;redotil 10|redotil sachet|racecadotril sachet|racecadotril 10|racecadotril 10 mg|hidrasec|redotil kids
sporlac;Sporlac;120 million spores;sachet;1 g sachet;Lactic Acid Bacillus;diarrhoea;sachet;sporlac|sporlak|sporlac sachet|sporlac powder|sporlac ds|spor lac
econorm;Econorm;250 mg;sachet;1 sachet;Saccharomyces boulardii;diarrhoea;sachet;econorm|econorm sachet|econorm 250|econorm powder|ekonorm
enterogermina;Enterogermina;2 billion spores/5 ml;syrup;5 ml vial;Bacillus clausii;diarrhoea;vial;enterogermina|entero germina|enterogermina vial|enterogermina 2 billion|enterogermina bottle
vizylac;Vizylac;5 billion spores;tablet;10 capsules;Lactobacillus;diarrhoea;strip;vizylac|vizilac|vizylac capsule|vizylac cap
zinc20;Zinc Dispersible Tablet;20 mg;tablet;10 tablets;Zinc Sulphate;diarrhoea;strip;zinc|zinc tablet|zinc 20|zinc dt|zinconia|zinc dispersible|zinc ki goli|z and d
metrogyl400;Metrogyl 400;400 mg;tablet;15 tablets;Metronidazole;diarrhoea;strip;metrogyl|metrogyl 400|metro 400|metrogil|metrojil|metrogyl400|metrogyl chaar sau
flagyl400;Flagyl 400;400 mg;tablet;15 tablets;Metronidazole;diarrhoea;strip;flagyl|flagyl 400|flagil|flagyl400
metrogylsyr;Metrogyl Suspension;200 mg/5 ml;syrup;60 ml;Metronidazole;diarrhoea;bottle;metrogyl syrup|metrogyl syp|metrogyl suspension|metrogyl bachchon wali|metrogyl 200 syp
eldoper;Eldoper;2 mg;tablet;10 capsules;Loperamide;diarrhoea;strip;eldoper|eldopar|loperamide|eldoper capsule|loperamide 2
ascorills;Ascoril LS;30 mg + 1 mg + 50 mg/5 ml;syrup;100 ml;Ambroxol + Levosalbutamol + Guaifenesin;respiratory;bottle;ascoril ls|ascoril l s|ascoril|ascoril syrup|ascoril ell ess|ascoril ls syp|askoril ls
ascorild;Ascoril D Plus;10 mg + 2 mg + 5 mg/5 ml;syrup;100 ml;Dextromethorphan + Chlorpheniramine + Phenylephrine;respiratory;bottle;ascoril d|ascoril d plus|ascoril dee|ascoril d syp|askoril d
benadryl;Benadryl Cough Formula;14.08 mg + 138 mg + 57.03 mg/5 ml;syrup;100 ml;Diphenhydramine + Ammonium Chloride + Sodium Citrate;respiratory;bottle;benadryl|benadryl syrup|benadryl cough|benadryl syp|bendryl|benadril|benadryl khansi
corexdx;Corex DX;10 mg + 4 mg/5 ml;syrup;100 ml;Dextromethorphan + Chlorpheniramine;respiratory;bottle;corex dx|corex d x|corex dx syrup|corex dee ex|corex dx syp
alex;Alex Syrup;10 mg + 2 mg + 5 mg/5 ml;syrup;100 ml;Dextromethorphan + Chlorpheniramine + Phenylephrine;respiratory;bottle;alex|alex syrup|alex syp|alex cough syrup|alex khansi
montairlc;Montair-LC;10 mg + 5 mg;tablet;10 tablets;Montelukast + Levocetirizine;respiratory;strip;montair lc|montair-lc|montairlc|montair l c|montair ell see|montek lc|montair elsi
montairlckid;Montair-LC Kid Syrup;4 mg + 2.5 mg/5 ml;syrup;60 ml;Montelukast + Levocetirizine;respiratory;bottle;montair lc kid|montair lc syrup|montair kid|montair lc syp|montair bachchon wali
levocetm;Levocet-M;5 mg + 10 mg;tablet;10 tablets;Levocetirizine + Montelukast;respiratory;strip;levocet m|levocet-m|levocetm|levocet em|levocet-m tablet
sinarest;Sinarest;500 mg + 10 mg + 2 mg;tablet;10 tablets;Paracetamol + Phenylephrine + Chlorpheniramine;respiratory;strip;sinarest|sinarest tablet|sinarest tab|sinaarest|sinarest cold|sinarest new
chestoncold;Cheston Cold;500 mg + 10 mg + 2 mg;tablet;10 tablets;Paracetamol + Phenylephrine + Chlorpheniramine;respiratory;strip;cheston cold|cheston|chestan cold|cheston tablet
vicksaction500;Vicks Action 500 Advanced;500 mg + 5 mg + 2 mg;tablet;10 tablets;Paracetamol + Phenylephrine + Chlorpheniramine;respiratory;strip;vicks action 500|vicks action|action 500|vicks tablet|vicks ki goli
dcold;D'Cold Total;500 mg + 5 mg + 2 mg;tablet;10 tablets;Paracetamol + Phenylephrine + Chlorpheniramine;respiratory;strip;d cold|dcold|d'cold total|d cold total|di cold|dcold total
azithral500;Azithral 500;500 mg;tablet;5 tablets;Azithromycin;respiratory;strip;azithral|azithral 500|azithral500|azithral paanch sau|azithro 500|azithral five hundred|azitral 500
azithral250;Azithral 250;250 mg;tablet;6 tablets;Azithromycin;respiratory;strip;azithral 250|azithral250|azithral dhai sau|azitral 250
azee500;Azee 500;500 mg;tablet;3 tablets;Azithromycin;respiratory;strip;azee|azee 500|azee500|aazee 500|azi 500
augmentin625;Augmentin 625 Duo;500 mg + 125 mg;tablet;10 tablets;Amoxicillin + Clavulanic Acid;respiratory;strip;augmentin|augmentin 625|augmentin duo|augmentin 625 duo|ogmentin|augmentin chhe sau pachchis|augmentin625
augmentinsyr;Augmentin Duo Suspension;228.5 mg/5 ml;syrup;30 ml;Amoxicillin + Clavulanic Acid;respiratory;bottle;augmentin syrup|augmentin duo syrup|augmentin syp|augmentin dry syrup|augmentin bachchon wali
moxikindcv;Moxikind-CV 625;500 mg + 125 mg;tablet;10 tablets;Amoxicillin + Clavulanic Acid;respiratory;strip;moxikind cv|moxikind-cv|moxikind cv 625|moxikind|moxi kind cv
taximo200;Taxim-O 200;200 mg;tablet;10 tablets;Cefixime;respiratory;strip;taxim o|taxim-o 200|taxim o 200|taxim|taxim-o|taksim o
asthalin;Asthalin Inhaler;100 mcg/dose;inhaler;200 doses;Salbutamol;respiratory;box;asthalin inhaler|asthalin|asthalin pump|asthalin puffer|asthalin 100|asthlin inhaler
levolin;Levolin Inhaler;50 mcg/dose;inhaler;200 doses;Levosalbutamol;respiratory;box;levolin inhaler|levolin|levolin pump|levolin puffer
foracort200;Foracort 200;6 mcg + 200 mcg/dose;inhaler;120 doses;Formoterol + Budesonide;respiratory;box;foracort 200|foracort|foracort inhaler|foracort 200 inhaler|forecort 200
seroflo250;Seroflo 250;25 mcg + 250 mcg/dose;inhaler;120 doses;Salmeterol + Fluticasone;respiratory;box;seroflo 250|seroflo|seroflo inhaler|serofloo 250
budecort05;Budecort Respules;0.5 mg/2 ml;respule;5 respules;Budesonide;respiratory;box;budecort|budecort respules|budecort 0.5|budecort respule|budecort aadha|budekort
duolinresp;Duolin Respules;1.25 mg + 500 mcg/2.5 ml;respule;5 respules;Levosalbutamol + Ipratropium;respiratory;box;duolin|duolin respules|duolin respule|duolin nebulizer|duolin resp
asthalinresp;Asthalin Respules;2.5 mg/2.5 ml;respule;5 respules;Salbutamol;respiratory;box;asthalin respules|asthalin respule|asthalin neb|asthalin nebulizer
mucinac600;Mucinac 600;600 mg;tablet;10 tablets;Acetylcysteine;respiratory;strip;mucinac|mucinac 600|mucinac effervescent|musinac 600|mucinac600
deriphyllin150;Deriphyllin Retard 150;150 mg;tablet;10 tablets;Etofylline + Theophylline;respiratory;strip;deriphyllin|deriphyllin retard|deriphyllin 150|deriphylline|deriphylin retard
otrivin;Otrivin Adult Nasal Drops;0.1% w/v;drops;10 ml;Xylometazoline;respiratory;bottle;otrivin|otrivin drops|otrivin nasal|otrivin adult|nak ki drops|otrivin nose drops
cetzine10;Cetzine;10 mg;tablet;10 tablets;Cetirizine;allergy;strip;cetzine|cetzine 10|cetrizine|cetirizine|setzine|cetzine tablet|cetrizin
cetzinesyr;Cetzine Syrup;5 mg/5 ml;syrup;60 ml;Cetirizine;allergy;bottle;cetzine syrup|cetzine syp|cetrizine syrup|cetzine bachchon wali|cetirizine syrup
okacet10;Okacet;10 mg;tablet;10 tablets;Cetirizine;allergy;strip;okacet|okacet 10|okasset|okacet tablet|oka cet
allegra120;Allegra 120;120 mg;tablet;10 tablets;Fexofenadine;allergy;strip;allegra|allegra 120|alegra 120|allegra one twenty|allegra120
allegra180;Allegra 180;180 mg;tablet;10 tablets;Fexofenadine;allergy;strip;allegra 180|alegra 180|allegra180|allegra one eighty
avil25;Avil 25;25 mg;tablet;15 tablets;Pheniramine;allergy;strip;avil|avil 25|avil25|avil tablet|aavil|avil pachchis
atarax25;Atarax 25;25 mg;tablet;15 tablets;Hydroxyzine;allergy;strip;atarax|atarax 25|atarex|atarax25|atarax pachchis
levocet5;Levocet;5 mg;tablet;10 tablets;Levocetirizine;allergy;strip;levocet|levocet 5|levocetrizine|levocet5|levo cet
glucondreg;Glucon-D Regular;200 g;sachet;200 g pouch;Glucose;heat;sachet;glucon d|glucon-d|glucond|glucon d regular|glucose powder|gluconde|glucon dee
glucondorange;Glucon-D Orange;200 g;sachet;200 g pouch;Glucose;heat;sachet;glucon d orange|glucon-d orange|glucond orange|glucon d santra|orange glucon d
enerzalorange;Enerzal Orange;100 g;sachet;100 g sachet;Glucose + Electrolytes;heat;sachet;enerzal|enerzal orange|enerjal|enerzal powder|enerzal sachet|energal
orslorange;ORSL Orange;200 ml;syrup;200 ml;Oral Rehydration Salts;heat;bottle;orsl|orsl orange|orsl 200|orsl ready to drink|o r s l|orsel|orsl santra
orslapple;ORSL Apple;200 ml;syrup;200 ml;Oral Rehydration Salts;heat;bottle;orsl apple|orsl seb|orsl apple 200|o r s l apple
lactocalamine;Lacto Calamine Lotion;120 ml;cream;120 ml;Calamine + Kaolin;heat;bottle;lacto calamine|lacto calamin|calamine lotion|lactocalamine|calamine|lacto calamine lotion
candid;Candid Cream;1% w/w;cream;15 g;Clotrimazole;fungal;tube;candid|candid cream|candid 15|kandid|candid tube|candid ointment
candidb;Candid-B Cream;1% + 0.025% w/w;cream;15 g;Clotrimazole + Beclomethasone;fungal;tube;candid b|candid-b|candidb|candid bee|candid b cream|kandid b
forcan150;Forcan 150;150 mg;tablet;1 tablet;Fluconazole;fungal;strip;forcan|forcan 150|fluconazole|fluconazole 150|forcan150|flucan 150
itaspor100;Itaspor 100;100 mg;tablet;10 capsules;Itraconazole;fungal;strip;itaspor|itaspor 100|itraconazole|itaspor100|itaspore
terbicip250;Terbicip 250;250 mg;tablet;7 tablets;Terbinafine;fungal;strip;terbicip|terbicip 250|terbinafine|terbinafine 250|terbisip 250
lamisilcream;Lamisil Cream;1% w/w;cream;15 g;Terbinafine;fungal;tube;lamisil|lamisil cream|lamisil tube|lamisil ointment
nizral;Nizral Cream;2% w/w;cream;15 g;Ketoconazole;fungal;tube;nizral|nizral cream|nizral 2%|nizaral|nizral tube
quadriderm;Quadriderm RF Cream;10 g;cream;10 g;Betamethasone + Gentamicin + Tolnaftate + Iodochlorhydroxyquin;fungal;tube;quadriderm|quadriderm rf|quadriderm cream|quadri derm|quadriderm tube
ciploxeye;Ciplox Eye/Ear Drops;0.3% w/v;drops;10 ml;Ciprofloxacin;eye;bottle;ciplox eye drops|ciplox drops|ciplox eye|ciplox|ciplox aankh ki drops|siplox eye drops
moxicipeye;Moxicip Eye Drops;0.5% w/v;drops;5 ml;Moxifloxacin;eye;bottle;moxicip|moxicip eye drops|moxicip drops|moxisip|moxicip eye|moxicip aankh ki drops
vigamox;Vigamox Eye Drops;0.5% w/v;drops;5 ml;Moxifloxacin;eye;bottle;vigamox|vigamox drops|vigamox eye drops|vigamoks
tobrex;Tobrex Eye Drops;0.3% w/v;drops;5 ml;Tobramycin;eye;bottle;tobrex|tobrex drops|tobrex eye drops|tobrex aankh
refreshtears;Refresh Tears;0.5% w/v;drops;10 ml;Carboxymethylcellulose;eye;bottle;refresh tears|refresh|refresh tears drops|refresh teers
tearsnaturale;Tears Naturale II;15 ml;drops;15 ml;Dextran + Hypromellose;eye;bottle;tears naturale|tears naturale 2|tears natural|teers naturale|naturale drops
akt4;AKT-4;75 mg + 150 mg + 400 mg + 275 mg;tablet;10 tablets;Isoniazid + Rifampicin + Pyrazinamide + Ethambutol;tb_watch;strip;akt 4|akt-4|akt4|a k t 4|akt char|akt four
forecox;Forecox;75 mg + 150 mg + 400 mg + 275 mg;tablet;10 tablets;Isoniazid + Rifampicin + Pyrazinamide + Ethambutol;tb_watch;strip;forecox|forecox tablet|forekox|fore cox|forcox
rimactazid;Rimactazid 150;150 mg + 75 mg;tablet;10 tablets;Rifampicin + Isoniazid;tb_watch;strip;rimactazid|rimactazid 150|rimactazid150|rimactazed|rimac
rcin450;R-Cin 450;450 mg;tablet;10 capsules;Rifampicin;tb_watch;strip;r cin|r-cin 450|rcin 450|rcin|r cin 450|arsin 450
isokin300;Isokin 300;300 mg;tablet;10 tablets;Isoniazid;tb_watch;strip;isokin|isokin 300|isokin300|inh 300|isoniazid 300|isoniazid
combutol800;Combutol 800;800 mg;tablet;10 tablets;Ethambutol;tb_watch;strip;combutol|combutol 800|combutol800|kombutol|ethambutol 800|ethambutol
pyzina750;Pyzina 750;750 mg;tablet;10 tablets;Pyrazinamide;tb_watch;strip;pyzina|pyzina 750|pyzina750|pyrazinamide|pyzina sat sau pachas
benadon40;Benadon 40;40 mg;tablet;10 tablets;Pyridoxine;tb_watch;strip;benadon|benadon 40|benadon40|b6 40|vitamin b6|pyridoxine 40|benadone
corex;Corex Cough Linctus;(codeine + chlorpheniramine)/5 ml;syrup;100 ml;Codeine + Chlorpheniramine;tb_watch;bottle;corex|corex syrup|corex linctus|corex codeine|corex cough|corex wali khansi
telma40;Telma 40;40 mg;tablet;15 tablets;Telmisartan;chronic_bp;strip;telma|telma 40|telma40|telmaa 40|telma chalis|telmisartan 40
telma20;Telma 20;20 mg;tablet;15 tablets;Telmisartan;chronic_bp;strip;telma 20|telma20|telma bees|telmisartan 20
telmah;Telma-H;40 mg + 12.5 mg;tablet;15 tablets;Telmisartan + Hydrochlorothiazide;chronic_bp;strip;telma h|telma-h|telmah|telma aitch|telma h 40
telmaam;Telma-AM;40 mg + 5 mg;tablet;15 tablets;Telmisartan + Amlodipine;chronic_bp;strip;telma am|telma-am|telmaam|telma a m|telma ae em
amlong5;Amlong 5;5 mg;tablet;15 tablets;Amlodipine;chronic_bp;strip;amlong|amlong 5|amlong5|amlong paanch|amlodipine 5|amlong five
amlong25;Amlong 2.5;2.5 mg;tablet;15 tablets;Amlodipine;chronic_bp;strip;amlong 2.5|amlong dhai|amlong 2 point 5|amlodipine 2.5
cilacar10;Cilacar 10;10 mg;tablet;10 tablets;Cilnidipine;chronic_bp;strip;cilacar|cilacar 10|cilacar10|silakar|cilacar das|cilnidipine
losar50;Losar 50;50 mg;tablet;15 tablets;Losartan;chronic_bp;strip;losar|losar 50|losar50|losartan 50|losar pachas|lozar 50
losarh;Losar-H;50 mg + 12.5 mg;tablet;15 tablets;Losartan + Hydrochlorothiazide;chronic_bp;strip;losar h|losar-h|losarh|losar aitch|losartan h
stamlo5;Stamlo 5;5 mg;tablet;15 tablets;Amlodipine;chronic_bp;strip;stamlo|stamlo 5|stamlo5|stamlo paanch|stamlo five
concor5;Concor 5;5 mg;tablet;10 tablets;Bisoprolol;chronic_bp;strip;concor|concor 5|concor5|concor paanch|konkor 5
metolarxl50;Metolar XL 50;50 mg;tablet;15 tablets;Metoprolol;chronic_bp;strip;metolar xl|metolar xl 50|metolar|metolar 50|metolar x l
ecosprin75;Ecosprin 75;75 mg;tablet;14 tablets;Aspirin;chronic_bp;strip;ecosprin|ecosprin 75|ecosprin75|ekosprin|ecosprin pachattar|aspirin 75
atorva10;Atorva 10;10 mg;tablet;15 tablets;Atorvastatin;chronic_bp;strip;atorva|atorva 10|atorva10|atorvastatin 10|atorva das|aatorva
rosuvas10;Rosuvas 10;10 mg;tablet;15 tablets;Rosuvastatin;chronic_bp;strip;rosuvas|rosuvas 10|rosuvas10|rosuvastatin|rosuvas das
clopitab75;Clopitab 75;75 mg;tablet;15 tablets;Clopidogrel;chronic_bp;strip;clopitab|clopitab 75|clopitab75|clopidogrel 75|clopitab pachattar
glycomet500;Glycomet 500;500 mg;tablet;20 tablets;Metformin;chronic_diabetes;strip;glycomet|glycomet 500|glycomet500|glycomet paanch sau|glycomit|metformin 500|glyco met
glycometsr500;Glycomet SR 500;500 mg;tablet;20 tablets;Metformin (sustained release);chronic_diabetes;strip;glycomet sr|glycomet sr 500|glycomet s r|glycomet sr500|glycomet slow
glycometgp1;Glycomet-GP 1;500 mg + 1 mg;tablet;15 tablets;Metformin + Glimepiride;chronic_diabetes;strip;glycomet gp|glycomet gp 1|glycomet-gp 1|glycomet gp1|glycomet g p 1|gp 1
galvusmet;Galvus Met 50/500;50 mg + 500 mg;tablet;15 tablets;Vildagliptin + Metformin;chronic_diabetes;strip;galvus met|galvus met 50/500|galvusmet|galvus|galvas met|galvus met fifty five hundred
janumet;Janumet 50/500;50 mg + 500 mg;tablet;15 tablets;Sitagliptin + Metformin;chronic_diabetes;strip;janumet|janumet 50/500|janumet 50|janu met|janumett
januvia100;Januvia 100;100 mg;tablet;7 tablets;Sitagliptin;chronic_diabetes;strip;januvia|januvia 100|januvia100|janu via|januvia sau
amaryl1;Amaryl 1;1 mg;tablet;30 tablets;Glimepiride;chronic_diabetes;strip;amaryl|amaryl 1|amaryl1|amaril|amaryl ek|amaryl one
amarylm1;Amaryl M 1;1 mg + 500 mg;tablet;15 tablets;Glimepiride + Metformin;chronic_diabetes;strip;amaryl m|amaryl m 1|amaryl-m|amaril m|amaryl m1
glimisavem2;Glimisave-M2;2 mg + 500 mg;tablet;10 tablets;Glimepiride + Metformin;chronic_diabetes;strip;glimisave m2|glimisave-m2|glimisave m 2|glimisave|glimi save m2
jalram;Jalra-M 50/500;50 mg + 500 mg;tablet;15 tablets;Vildagliptin + Metformin;chronic_diabetes;strip;jalra m|jalra-m|jalra m 50/500|jalram|jalra
tradjenta5;Tradjenta 5;5 mg;tablet;10 tablets;Linagliptin;chronic_diabetes;strip;tradjenta|tradjenta 5|tradjenta5|trajenta|trajenta 5
mixtard;Human Mixtard 30/70;40 IU/ml;injection;10 ml vial;Human Insulin (biphasic);chronic_diabetes;vial;mixtard|mixtard 30/70|human mixtard|mixtard insulin|mixtard vial|mixtard 30 70
pand;Pan-D;40 mg + 30 mg;tablet;15 capsules;Pantoprazole + Domperidone;other;strip;pan d|pan-d|pand|pan dee|pan dee capsule|pan d capsule|pan di
pantopd;Pantop-D;40 mg + 30 mg;tablet;15 capsules;Pantoprazole + Domperidone;other;strip;pantop d|pantop-d|pantopd|pantop dee|pantap d|pantop di
pan40;Pan 40;40 mg;tablet;15 tablets;Pantoprazole;other;strip;pan 40|pan40|pan chalis|pan forty|pantoprazole 40|pan
pantop40;Pantop 40;40 mg;tablet;15 tablets;Pantoprazole;other;strip;pantop 40|pantop|pantop40|pantap 40|pantop chalis
razod;Razo-D;20 mg + 30 mg;tablet;15 capsules;Rabeprazole + Domperidone;other;strip;razo d|razo-d|razod|razo dee|rajo d
omez20;Omez 20;20 mg;tablet;15 capsules;Omeprazole;other;strip;omez|omez 20|omez20|omeez|omez bees|omeprazole 20
rantac150;Rantac 150;150 mg;tablet;30 tablets;Ranitidine;other;strip;rantac|rantac 150|rantak|rantac150|ranitidine 150
digenegel;Digene Gel;200 ml;syrup;200 ml;Antacid (Aluminium + Magnesium + Simethicone);other;bottle;digene|digene gel|digene syrup|digene gel mint|digene bottle|dijene
cyclopam;Cyclopam;20 mg + 500 mg;tablet;10 tablets;Dicyclomine + Paracetamol;other;strip;cyclopam|cyclopam tablet|ciclopam|cyclopam pet dard|cyclopam tab
meftalspas;Meftal-Spas;250 mg + 10 mg;tablet;10 tablets;Mefenamic Acid + Dicyclomine;other;strip;meftal spas|meftal-spas|meftalspas|meftal spas tablet|meftal s
voveran50;Voveran 50;50 mg;tablet;10 tablets;Diclofenac;other;strip;voveran|voveran 50|voveran50|voveran tablet|voweran
zerodolsp;Zerodol-SP;100 mg + 325 mg + 15 mg;tablet;10 tablets;Aceclofenac + Paracetamol + Serratiopeptidase;other;strip;zerodol sp|zerodol-sp|zerodol s p|zerodol|zerodol esp
volini;Volini Gel;30 g;cream;30 g;Diclofenac + Methyl Salicylate + Menthol;other;tube;volini|volini gel|volini tube|volini spray gel|voliny
betadine;Betadine Ointment;5% w/w;cream;15 g;Povidone Iodine;other;tube;betadine|betadine ointment|betadine cream|betadin|betadine tube
soframycin;Soframycin Skin Cream;1% w/w;cream;30 g;Framycetin;other;tube;soframycin|soframycin cream|soframicin|soframycin tube|soframycin ointment
shelcal500;Shelcal 500;500 mg;tablet;15 tablets;Calcium + Vitamin D3;other;strip;shelcal|shelcal 500|shelcal500|shelkal|shelcal paanch sau|calcium shelcal
neurobionforte;Neurobion Forte;Vitamin B complex;tablet;30 tablets;Vitamin B1 + B6 + B12;other;strip;neurobion|neurobion forte|neurobion f|nurobion forte|neuro bion|neurobion fort
becosules;Becosules;Vitamin B complex + Vitamin C;tablet;20 capsules;Vitamin B complex + Vitamin C;other;strip;becosules|becosule|becosules capsule|beacosules|becosules cap
zincovit;Zincovit;Multivitamin + Zinc;tablet;15 tablets;Multivitamin + Minerals;other;strip;zincovit|zinkovit|zincovit tablet|zincovit tab|zinc ovit|zincovit multivitamin
limcee500;Limcee 500;500 mg;tablet;15 tablets;Vitamin C;other;strip;limcee|limcee 500|limcee500|limsee|vitamin c|limcee chewable
evion400;Evion 400;400 mg;tablet;10 capsules;Vitamin E;other;strip;evion|evion 400|evion400|evion capsule|evion cap
liv52;Liv.52 Syrup;200 ml;syrup;200 ml;Herbal liver tonic;other;bottle;liv 52|liv52|liv.52|liv 52 syrup|liv fifty two|liv 52 syp
dexorange;Dexorange Syrup;200 ml;syrup;200 ml;Iron + Folic Acid + Vitamin B12;other;bottle;dexorange|dex orange|dexorange syrup|dexorange syp|dexoranj
uprised3;Uprise-D3 60K;60000 IU;tablet;4 capsules;Cholecalciferol;other;strip;uprise d3|uprise-d3|uprise d3 60k|uprise|uprise d three|uprise 60k
cremaffin;Cremaffin Plus;225 ml;syrup;225 ml;Liquid Paraffin + Milk of Magnesia + Sodium Picosulfate;other;bottle;cremaffin|cremaffin plus|cremafin|cremaffin syrup|cremaffin syp
unwanted72;Unwanted 72;1.5 mg;tablet;1 tablet;Levonorgestrel;other;strip;unwanted 72|unwanted72|unwanted seventy two|unwanted|unwanted 72 tablet
"""
