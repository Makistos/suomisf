import csv
import mysql.connector

categoryMap = {
"Prix Apollo": "Paras romaani",
"Superior Achievement in a Novel": "Paras romaani",
"Superior Achievement in a First Novel": "Paras ensiromaani",
"Superior Achievement in a Young Adult Novel": "Paras nuortenkirja",
"Superior Achievement in a Work for Young Readers": "Paras nuortenkirja",
"Superior Achievement in Long Fiction": "Paras pitkä fiktio",
"Superior Achievement in a Novella": "Paras pienoisromaani",
"Superior Achievement in a Novelet": "Paras pitkä novelli",
"Superior Achievement in Short Fiction": "Paras lyhyt fiktio",
"Superior Achievement in a Fiction Collection": "Paras kokoelma",
"Superior Achievement in an Anthology": "Paras antologia",
"Best Science Fiction Novel": "Paras sf-romaani",
"Carnegie Medal": "Carnegie-mitali",
"August Derleth Award for Best Horror Novel": "Paras kauhuromaani",
"August Derleth Fantasy Award (Best Novel)": "Paras romaani",
"Robert Holdstock Award for Best Fantasy Novel": "Paras fantasiaromaani",
"Best Novella": "Paras pienoisromaani",
"Best Short Fiction": "Paras lyhyt fiktio",
"Best Short Story": "Paras novelli",
"Best Collection": "Paras kokoelma",
"Best Anthology": "Paras antologia",
"Best Novel": "Paras romaani",
"Best Book for Younger Readers": "Paras nuortenkirja",
"Science Fiction": "Paras scifi-romaani",
"Fantasy": "Paras fantasiaromaani",
"Paranormal Fantasy": "Paras paranormaali fantasia -romaani",
"Horror": "Paras kauhuromaani",
"Young Adult Fantasy & Science Fiction": "Paras nuorten sf-romaani",
"Young Adult Fantasy": "Paras nuorten sf-romaani",
"Young Adult Fiction": "Paras nuortenkirja",
"Middle Grade & Children's": "Paras lastenkirja",
"Best Novelette": "Paras pitkä novelli",
"Best SF Novel": "Paras scifi-romaani",
"Best Fantasy Novel": "Paras fantasiaromaani",
"Best Horror Novel": "Paras kauhuromaani",
"Best Horror/Dark Fantasy Novel": "Paras kauhu/synkkä fantasia-romaani",
"Best First Novel": "Paras ensiromaani",
"Best Young Adult Book": "Paras nuortenkirja",
"Best Single Author Collection": "Paras kokoelma",
"Mythopoeic Fantasy Award": "Paras romaani",
"Mythopoeic Fantasy Award for Adult Literature": "Paras romaani",
"Mythopoeic Fantasy Award for Young Adult Literature": "Paras nuortenkirja",
"Mythopoeic Fantasy Award for Children's Literature": "Paras lastenkirja",
"Novel": "Paras romaani",
"Novella": "Paras pienoisromaani",
"Novelette": "Paras pitkä novelli",
"Short Story": "Paras novelli",
"Philip K. Dick Award": "Paras romaani",
"Best Long Form Alternate History": "Paras vaihtoehtoishistoria (pitkä muoto)",
"Best Short Form Alternate History": "Paras vaihtoehtoishistoria (lyhyt muoto)",
"Best Short Science Fiction": "Paras scifi-novelli",
"Best Long Fiction": "Paras pitkä fiktio",
"Best Anthology/Collection (old)": "Paras kokoelma",
"Andre Norton Award": "Paras nuorten sf-romaani",
"Andre Norton Nebula Award for Middle Grade and Young Adult Fiction ": "Paras nuorten sf-romaani",
"Roman étranger": "Paras ulkomainen romaani",
"Nouvelle étrangère": "Paras ulkomainen novelli",
"Roman jeunesse étranger": "Paras ulkomainen nuorten romaani",
"Bester ausländischer SF-Roman": "Paras ulkomainen romaani",
"Mejor novela - Best Novel": "Paras romaani",
"Mejor novela extranjera - Best Foreign Novel": "Paras ulkomainen romaani",
"Mejor cuento extranjero - Best Foreign Story": "Paras ulkomainen novelli"
}

awardMap = {
    "Apollo": "Prix Tour-Apollo Award",
    "Bram Stoker Award": "Bram Stoker Award",
    "Arthur C. Clarke -palkinto": "Arthur C. Clarke Award",
    "Campbell Memorial Award": "John W. Campbell Memorial Award",
    "Carnegie-mitali": "Carnegie Medal for Writing",
    "British Fantasy Award": "British Fantasy Award",
    "British Science Fiction Award": "British Science Fiction Award",
    "Goodreads Choice Awards": "Goodreads Choice Awards",
    "Hugo": "Hugo Award",
    "Imaginaire": "Grand Prix de l'Imaginaire",
    "Kurd Lasswitz": "Kurd-Laßwitz-Preis",
    "Locus": "Locus Poll Award",
    "Mythopoeic": "Mythopoeic Award",
    "Nebula": "Nebula Award",
    "Norton": "Andre Norton Award for Young Adult Science Fiction and Fantasy",
    "Philip K. Dick Award": "Philip K. Dick Award",
    "Premio Ignotus": "Premio Ignotus",
    "Retro Hugo": "Retro Hugo Award",
    "Shirley Jackson Award": "Shirley Jackson Award",
    "Sidewise": "Sidewise Awards for Alternate History",
    "Theodore Sturgeon Award": "Theodore Sturgeon Memorial Award",
    "World Fantasy Award": "World Fantasy Award"
}
# Read award info from awards.tsv
awards = []
with open("awards.tsv") as fp:
    # Read tsv file:
    reader = csv.DictReader(fp, delimiter='\t')
    next(reader)
    for row in reader:
        award = {
            'year': row['year'],
            'award_type': row['award_type'],
            'award_category': row['award_category'],
            'title': row['title'],
            'author': row['author'],
            'item_type': row['item_type']
        }
        awards.append(award)

# Read categories from database

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",
    database="suomisf"
)

cursor = conn.cursor()

cursor.execute("SELECT id, name, type FROM awardcategory")
db_categories = cursor.fetchall()

# This map holds original category names and their corresponding database IDs,
# with ids in the first and second positions of the tuple.
# The first value is for novels, the second for short stories.
category_id_map = {
}
for ac, cat in categoryMap.items():
    found = False
    # print(cat[0], cat[1], cat[2])
    for db_cat in db_categories:
        if cat == db_cat[1]:
            found = True
            item = (0, 0)
            if cat not in category_id_map:
                # First value is for novels, second for short stories
                category_id_map[ac] = (0, 0)
            if db_cat[2] == 1:
                category_id_map[ac] = (db_cat[0], item[1])
            elif db_cat[2] == 2:
                category_id_map[ac] = (item[0], db_cat[0])
    if found == False:
        print(f"Category {ac}:{cat} not found in database")

print("Category ID map:")
for k, v in category_id_map.items():
    print(f"{k}: {v}")
# Now we can find category id by first looking for the mapped category name
# in categoryMap and then using that value to find the id in category_id_map

# Read awards from database
cursor.execute("SELECT id, name FROM award")
db_awards = cursor.fetchall()

# Create a map of award names to their IDs
award_id_map = {}
for award in db_awards:
    if award[1] in awardMap:
        award_id_map[awardMap[award[1]]] = award[0]
    else:
        print(f"Award {award[1]} not found in awardMap")

# Check for missing awards
missing_awards = set(awardMap.values()) - set(award_id_map.keys())
if missing_awards:
    print("\nAwards in awardMap but missing from database:")
    for award in missing_awards:
        print(f"- {award}")

print(award_id_map)

def createTsvRow(outfile: any, itemType: str, year: int, orig_title: str, author: str, title: str, awarded: str, award_type: str, award_category: str, our_category: str = ""):
    outfile.write(f"{itemType}\t{year}\t{orig_title}\t{author}\t{title}\t{awarded}\t{award_type}\t{award_category}\t{our_category}\n")

with open('award_check_results.txt', 'w', encoding='utf-8') as outfile:
    outfile.write("#Type\tYear\tOriginal title\tAuthor\tTitle\tStatus\tAward type\tAward category\tDatabase category\n")
    for award in awards:
        found = True
        # Check work
        if award['award_category'] in categoryMap:
            our_category = categoryMap[award['award_category']]
        else:
            our_category = ""
        if award['award_type'] in award_id_map:
            if award['item_type'] in ('Work', 'Both'):
                cursor.execute('SELECT id, title, orig_title FROM work WHERE orig_title = %s', (award['title'],))
                work = cursor.fetchall()
                if work:
                    work_id = work[0][0]
                    cursor.execute("SELECT * FROM awarded WHERE work_id = %s AND award_id = %s", (work_id, award_id_map[award['award_type']]))
                    awarded = cursor.fetchall()
                    if award['item_type'] == "short story":
                        status = "Wrong type"
                    elif awarded:
                        status = "Awarded"
                    else:
                        status = "Not awarded"
                    createTsvRow(outfile, "Work", award['year'], award['title'], award['author'], work[0][1], status, award['award_type'], award['award_category'], our_category)
                    found = True
                else:
                    found = False
            if award['item_type'] in ('Short story', 'Both'):
                # Check short story
                cursor.execute("SELECT id, title, orig_title FROM shortstory WHERE orig_title = %s", (award['title'],))
                shortstory = cursor.fetchall()
                if shortstory:
                    shortstory_id = shortstory[0][0]
                    cursor.execute("SELECT * FROM awarded WHERE story_id = %s AND award_id = %s", (shortstory_id, award_id_map[award['award_type']]))
                    awarded = cursor.fetchall()
                    if award['item_type'] == "work":
                        status = "Wrong type"
                    elif awarded:
                        status = "Awarded"
                    else:
                        status = "Not awarded"
                    createTsvRow(outfile, "Short story", award['year'],award['title'], award['author'], shortstory[0][1], status, award['award_type'], award['award_category'], our_category)
                    found = True
                else:
                    found = False
            if found == False:
                # Not found in database
                createTsvRow(outfile, award['item_type'], award['year'], award['title'], award['author'], "???", "Not found in database", award['award_type'], award['award_category'], our_category)


print(f"Results have been written to award_check_results.txt")

# Close the database connection
cursor.close()
conn.close()
# Close the output file
outfile.close()