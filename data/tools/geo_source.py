"""Geography and people source tables for the FirstSign seed data.

Everything here is a simulated demo dataset. Pin codes, area names, wards and
landmarks are real place names used for realism; centroids, populations and
household counts are rough estimates, not survey figures.
"""

from __future__ import annotations

# pin, area, BMC ward, lat, lng, catchment population estimate, default chemist language
PINCODES: list[tuple[str, str, str, float, float, int, str]] = [
    ("400070", "Kurla West", "L", 19.0730, 72.8800, 310000, "hi"),
    ("400024", "Kurla East / Nehru Nagar", "L", 19.0750, 72.8920, 260000, "hi"),
    ("400022", "Sion / Chunabhatti", "F North", 19.0450, 72.8660, 240000, "mr"),
    ("400037", "Antop Hill / Sion Koliwada", "F North", 19.0260, 72.8650, 180000, "mr"),
    ("400017", "Dharavi", "G North", 19.0430, 72.8540, 380000, "hi"),
    ("400019", "Matunga", "F North", 19.0270, 72.8570, 150000, "mr"),
    ("400031", "Wadala", "F North", 19.0160, 72.8570, 140000, "mr"),
    ("400071", "Chembur", "M West", 19.0560, 72.8990, 230000, "mr"),
    ("400088", "Mankhurd", "M East", 19.0480, 72.9320, 290000, "hi"),
    ("400043", "Govandi", "M East", 19.0550, 72.9200, 270000, "hi"),
    ("400086", "Ghatkopar West", "N", 19.0860, 72.9080, 220000, "mr"),
    ("400077", "Ghatkopar East", "N", 19.0850, 72.9250, 210000, "mr"),
    ("400072", "Sakinaka", "L", 19.1040, 72.8880, 200000, "hi"),
    ("400050", "Bandra West", "H West", 19.0600, 72.8290, 170000, "en"),
    ("400051", "Bandra East", "H East", 19.0680, 72.8480, 190000, "hi"),
    ("400055", "Santacruz East / Kalina", "H East", 19.0790, 72.8580, 160000, "hi"),
    ("400069", "Andheri East", "K East", 19.1136, 72.8697, 200000, "hi"),
    ("400058", "Andheri West", "K West", 19.1250, 72.8400, 190000, "en"),
    ("400093", "Marol / MIDC", "K East", 19.1190, 72.8800, 170000, "hi"),
    ("400076", "Powai", "S", 19.1176, 72.9060, 180000, "en"),
]

# pin -> six (name, landmark, households) tuples
LOCALITIES: dict[str, list[tuple[str, str, int]]] = {
    "400070": [
        ("Kasaiwada", "Near Kurla station (west) subway", 1800),
        ("Qureshi Nagar", "Off LBS Marg, near the flyover", 2600),
        ("Kajupada", "Kurla West, near the nullah", 2100),
        ("Bail Bazaar", "Market lane near Kurla bus depot", 900),
        ("Kamani", "Kamani junction chawl cluster", 1500),
        ("Hall Road", "Behind Phoenix Marketcity, building cluster", 700),
    ],
    "400024": [
        ("Nehru Nagar", "Kurla East, near Kurla Terminus (LTT) colony", 3200),
        ("Bhim Nagar", "Kurla East, near the water tank lane", 1400),
        ("Kurla Terminus Colony", "Railway quarters near LTT", 800),
        ("Kapadia Nagar", "Chawl cluster off Kalpana Cinema road", 1900),
        ("Sundar Baug", "Lane behind Kurla East market", 1100),
        ("Shivaji Nagar Kurla", "Near Kurla East ST depot", 1700),
    ],
    "400022": [
        ("Pratiksha Nagar", "Sion, BEST colony and surrounding chawls", 2900),
        ("Chunabhatti Swadeshi Mill", "Swadeshi Mill compound, Chunabhatti", 2200),
        ("Everard Nagar", "Sion-Chunabhatti, near the Eastern Express Highway", 2400),
        ("Sion Circle", "Market lanes around Sion Circle", 1000),
        ("Sion Fort", "Near Sion Fort hill, old building cluster", 900),
        ("Sion Hospital Road", "Lanes opposite the municipal hospital", 1300),
    ],
    "400037": [
        ("Sangam Nagar", "Antop Hill, hillside slum pocket", 3600),
        ("CGS Colony", "Antop Hill, central government quarters", 1500),
        ("Koliwada", "Sion Koliwada, fishing community lanes", 1200),
        ("Barkat Ali Naka", "Antop Hill market junction", 1000),
        ("Shaikh Misry Road", "Chawl cluster near Antop Hill", 1800),
        ("Vidyalankar Lane", "Building cluster near the college", 700),
    ],
    "400017": [
        ("Kumbharwada", "Dharavi potters' colony", 2100),
        ("90 Feet Road", "Dharavi main road, shop-house lanes", 2600),
        ("Social Nagar", "Dharavi, near the Mahim Sion link road", 3000),
        ("Transit Camp", "Dharavi, rehabilitation buildings", 1900),
        ("Dharavi Koliwada", "Fishing village pocket by the creek", 1100),
        ("Muslim Nagar", "Dharavi, dense chawl lanes", 2700),
    ],
    "400019": [
        ("Matunga Labour Camp", "Matunga East, near Dharavi border", 3400),
        ("King's Circle", "Building cluster near King's Circle station", 1300),
        ("Five Gardens", "Matunga East, housing societies", 800),
        ("Telang Road", "Matunga East, market and chawls", 1100),
        ("Mysore Colony", "Matunga, near the Mysore Association", 600),
        ("Matunga Road", "Lanes near Matunga Road station", 1500),
    ],
    "400031": [
        ("Wadala Truck Terminal", "Truck terminal and surrounding slum lanes", 2800),
        ("Bhakti Park", "Wadala East, building cluster", 1200),
        ("Sangam Nagar Wadala", "Wadala, near the Sion-Wadala link", 2000),
        ("BPT Colony", "Port Trust quarters, Wadala", 1600),
        ("Anand Nagar Wadala", "Wadala West, chawl cluster", 1400),
        ("Wadala Station Road", "Market lane by Wadala Road station", 900),
    ],
    "400071": [
        ("Chembur Camp", "Sindhi colony, near Chembur Camp", 2000),
        ("Diamond Garden", "Chembur, society cluster near the garden", 1100),
        ("Ghatla Gaon", "Ghatla village, dense lanes", 2500),
        ("Chembur Naka", "Market junction on the Eastern Freeway side", 1400),
        ("Sahakar Nagar", "Chembur, housing society colony", 1300),
        ("Tilak Nagar Chembur", "Near Tilak Nagar station, chawls", 1800),
    ],
    "400088": [
        ("Mandala", "Mankhurd, near the creek", 3100),
        ("Lallubhai Compound", "Mankhurd, large rehabilitation colony", 3800),
        ("Mahul Village", "Mahul, near the refinery belt", 1900),
        ("Maharashtra Nagar", "Mankhurd, chawl cluster", 2500),
        ("Mankhurd Station Road", "Market lane near Mankhurd station", 900),
        ("Sathe Nagar", "Mankhurd, near the Deonar side", 2200),
    ],
    "400043": [
        ("Baiganwadi", "Govandi, dense hutment lanes", 3900),
        ("Shivaji Nagar Govandi", "Govandi, near the station", 3300),
        ("Rafique Nagar", "Govandi, near the Deonar dumping road", 2600),
        ("Govandi Station Road", "Market lane near Govandi station", 1100),
        ("Janta Nagar", "Govandi, chawl cluster", 2000),
        ("Kamla Raman Nagar", "Govandi, settlement near Baiganwadi", 2800),
    ],
    "400086": [
        ("Asalpha", "Asalpha village, near the metro station", 2700),
        ("Jagdusha Nagar", "Ghatkopar West, near the hill road", 3000),
        ("Barve Nagar", "Ghatkopar West, building cluster", 1200),
        ("Laxmi Baug", "Ghatkopar West, chawl and market lanes", 1500),
        ("Station Road Market", "Ghatkopar station market", 800),
        ("Kirol Road", "Near Vidyavihar, society cluster", 1000),
    ],
    "400077": [
        ("Pant Nagar", "Ghatkopar East, large chawl colony", 3500),
        ("Rajawadi", "Ghatkopar East, near Rajawadi hospital", 1900),
        ("Ramabai Ambedkar Nagar", "Ghatkopar East, hillside settlement", 4200),
        ("Kamraj Nagar", "Ghatkopar East, near the Eastern Express Highway", 2500),
        ("Parsiwadi", "Ghatkopar East, mixed buildings", 1000),
        ("Laxmi Nagar Ghatkopar", "Ghatkopar East, chawl lanes", 1700),
    ],
    "400072": [
        ("Sakinaka Junction", "Market junction on Andheri-Kurla Road", 1200),
        ("Khairani Road", "Sakinaka, small industrial units and chawls", 2800),
        ("Jarimari", "Sakinaka, dense lanes near the nullah", 3100),
        ("Sangharsh Nagar", "Chandivali-Sakinaka, hillside colony", 3000),
        ("Safed Pool", "Under the Safed Pool bridge, lanes around", 1900),
        ("Mohili Village", "Sakinaka, village pocket", 1300),
    ],
    "400050": [
        ("Pali Hill", "Bandra West, society cluster", 600),
        ("Bandstand", "Sea-facing building cluster", 500),
        ("Hill Road", "Bandra West, shops and buildings", 900),
        ("Bazaar Road", "Market lanes near Bandra station", 1000),
        ("Chimbai Village", "Koliwada pocket, Bandra West", 1100),
        ("Ranwar Village", "Bandra West, gaothan lanes", 800),
    ],
    "400051": [
        ("Bharat Nagar", "Bandra East, near the Western Express Highway", 3200),
        ("Behrampada", "Bandra East, dense slum pocket", 3800),
        ("Garib Nagar", "Bandra East, by the railway line", 2900),
        ("Kherwadi", "Bandra East, chawl cluster", 2400),
        ("Nirmal Nagar", "Bandra East, housing colony", 1200),
        ("Kala Nagar", "Near the Bandra Reclamation side", 900),
    ],
    "400055": [
        ("Kalina Village", "Santacruz East, gaothan lanes", 1300),
        ("Kolivery Village", "Santacruz East, fishing community", 1000),
        ("Golibar", "Santacruz East, dense settlement", 3500),
        ("Vakola", "Near Vakola bridge, chawl cluster", 2600),
        ("Prabhat Colony", "Santacruz East, housing colony", 1100),
        ("Nehru Road", "Santacruz East market stretch", 800),
    ],
    "400069": [
        ("Chakala", "Andheri East, near the airport road", 1500),
        ("JB Nagar", "Andheri East, mixed chawls and buildings", 2800),
        ("Marol Maroshi Road", "Andheri East, shops and chawls", 1600),
        ("Telli Galli", "Andheri East, old lanes", 900),
        ("Gundavali", "Andheri East, near the metro station", 1200),
        ("Sahar Road", "Andheri East, near the airport", 1400),
    ],
    "400058": [
        ("Azad Nagar", "Andheri West, market and chawls", 2600),
        ("DN Nagar", "Andheri West, society cluster", 1100),
        ("Four Bungalows", "Andheri West, residential lanes", 900),
        ("Versova Koliwada", "Fishing community by the beach", 1700),
        ("Amboli", "Andheri West, near the Western Express Highway", 1500),
        ("Seven Bungalows", "Andheri West, seafront buildings", 700),
    ],
    "400093": [
        ("Marol Village", "Marol gaothan lanes", 1900),
        ("Mahakali Caves Road", "Chawl cluster along the caves road", 2200),
        ("SEEPZ Gate", "Lanes around the SEEPZ gate", 1000),
        ("Marol Naka", "Marol junction, market and chawls", 1800),
        ("Hanuman Nagar Marol", "Hillside settlement near MIDC", 2400),
        ("MIDC Road", "Industrial estate worker housing", 1300),
    ],
    "400076": [
        ("Hiranandani Gardens", "Powai, large society township", 1200),
        ("Chandivali", "Powai, village and chawl pocket", 2300),
        ("Saki Vihar Road", "Powai, residential and shops", 1000),
        ("Powai Lake side", "Lanes near the lake", 800),
        ("Jai Bhim Nagar", "Powai, large settlement near the hills", 4000),
        ("Tunga Village", "Powai, gaothan lanes", 1100),
    ],
}

# asha_id, first name, pin, language. Several share a pin so the officer list has choices.
ASHAS: list[tuple[str, str, str, str]] = [
    ("ASHA01", "Sunita", "400070", "hi"),
    ("ASHA02", "Shabana", "400070", "hi"),
    ("ASHA03", "Rekha", "400024", "hi"),
    ("ASHA04", "Lata", "400024", "hi"),
    ("ASHA05", "Mangal", "400022", "mr"),
    ("ASHA06", "Sarita", "400022", "mr"),
    ("ASHA07", "Kavita", "400037", "mr"),
    ("ASHA08", "Farida", "400017", "hi"),
    ("ASHA09", "Meena", "400088", "hi"),
    ("ASHA10", "Pushpa", "400043", "hi"),
    ("ASHA11", "Anita", "400086", "mr"),
    ("ASHA12", "Savita", "400077", "mr"),
]

SHOP_PREFIX = [
    "Shree Ganesh", "Sai", "Om Sai", "Jeevan", "New Jeevan", "Lifeline", "Shree Krishna", "Gupta",
    "Mahalaxmi", "Raj", "Balaji", "Sanjivani", "Aarogya", "Noor", "Al-Shifa", "City", "Modern",
    "Healthwell", "Shiv", "Swami Samarth", "Siddhivinayak", "Ambika", "Bharat", "Wellness", "Kamal",
    "Hind", "Janata", "Pooja", "Navjeevan", "Arihant", "Sagar", "Shree Datta", "Mauli", "Amar",
    "Royal", "Care Plus", "Metro", "Unity", "Star", "Rohit", "Sai Baba", "Jai Ambe", "Gurukripa",
    "Vighnaharta", "Shraddha", "Kohinoor", "Madina", "Prakash", "Sunrise", "Lotus",
]
SHOP_TYPE = ["Medical", "Medical Stores", "Chemist", "Medico", "Pharmacy", "Medical & General Stores", "Drug House"]
OWNER_FIRST_NAMES = [
    "Ramesh", "Sunil", "Imran", "Farhan", "Prakash", "Meena", "Sanjay", "Abdul", "Joseph", "Mohammed",
    "Suresh", "Dinesh", "Kiran", "Vikas", "Anil", "Rakesh", "Nilesh", "Ganesh", "Yusuf", "Salim",
    "Deepak", "Mahesh", "Pravin", "Santosh", "Rajesh", "Nasir", "Kamlesh", "Jayesh", "Hitesh", "Amit",
    "Vijay", "Ashok", "Sachin", "Rohit", "Tushar", "Bhavesh", "Shabbir", "Irfan", "Anwar", "Manoj",
    "Sheetal", "Pooja", "Neha", "Smita", "Rupali", "Sharmila", "Naseem", "Jyoti", "Archana", "Ketan",
]
