import requests
from bs4 import BeautifulSoup
import sys
import re

# List of ISFDB award category pages to scrape
award_urls = [
    ### Apollo award
    # Apollo award for best science fiction novel (Prix Apollo)
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?16+0", 0),

    ### Bram Stoker award
    # Superior Achievement in a Novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?498+0", 0),
    # Superior Achievement in a First Novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?497+0", 0),
    # Superior Achievement in a Young Adult Novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?632+0", 0),
    # Superior Achievement in a Work for Young Readers
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?503+0", 0),
    # Superior Achievement in Long Fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?507+0", 0),
    # Superior Achievement in a Novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?500+0", 2),
    # Superior Achievement in a Novelet
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?499+0", 1),
    # Superior Achievement in Short Fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?510+0", 1),
    # Superior Achievement in a Fiction Collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?496+0", 0),
    # Superior Achievement in an Anthology
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?505+0", 0),

    ### Arthur C. Clarke award
    # Arthur C. Clarke award for best science fiction novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?140+0", 0),

    ### John W. Campbell award
    # John W. Campbell award for best science fiction novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?130+0", 0),

    ### Carnegie medal
    # Carnegie medal for best children's book
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?618+0", 0),

    ### British Fantasy awards
    # August Derleth award for best horror novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?586+0", 0),
    # August Derleth Fantasy award for best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?75+0", 0),
    # Robert Holdstock Award for Best Fantasy Novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?585+0", 0),
    # Best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?88+0", 2),
    # Best short fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?89+0", 1),
    # Best short story
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?90+0", 1),
    # Best collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?80+0", 0),
    # Best anthology
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?76+0", 0),

    ### British Science Fiction awards
    # Best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?120+0", 0),
    # Best book for young readers
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?1028+0", 0),
    # Best short fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?121+0", 1),
    # Best collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?1096+0", 0),

    ### Goodreads Choice awards
    # Best science fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?731+0", 0),
    # Best fantasy
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?730+0", 0),
    # Best paranormal fantasy
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?736+0", 0),
    # Best horror
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?732+0", 0),
    # Young Adult Fantasy & Science Fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?733+0", 0),
    #  Young Adult Fantasy
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?735+0", 0),
    # Young Adult Fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?738+0", 0),
    # Middle Grade & Children's
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?734+0", 0),

    ### Hugo awards
    # Hugo awards, best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?261+0", 0),
    # Hugo awards, best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?262+0", 2),

    ### Grand Prix de l'Imaginaire
    # Grand Prix de l'Imaginaire, best foreign novel
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?290+0', 0),
    # Grand Prix de l'Imaginaire, best foreign short story
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?287+0', 1),
    # Grand Prix de l'Imaginaire, best foreign youth novel
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?699+0', 0),

    ### Kurd-Laßwitz-Preis
    # Kurd-Laßwitz-Preis, best foreign science fiction novel
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?686+0', 0),
    # Kurd-Laßwitz-Preis, best foreign novel
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?685+0', 0),

    ### Locus awards
    # Locus awards, best science fiction novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?375+0", 0),
    # Locus awards, best fantasy novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?347+0", 0),
    # Locus awards, best horror novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?350+0", 0),
    # Locus awards, best horror/dark fantasy novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?351+0", 0),
    # Locus awards, best first novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?349+0", 0),
    # Locus awards, best young adult book
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?382+0", 0),
    # Locus awards, best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?361+0", 2),
    # Locus awards, best novelette
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?360+0", 1),
    # Locus awards, best short story
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?378+0", 1),
    # Locus awards, best short fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?377+0", 1),
    # Locus awards, best collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?338+0", 0),
    # Locus awards, best single author collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?379+0", 0),
    # Locus awards, best anthology
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?329+0", 0),

    ### Mythopoeic award
    # Fantasy award
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?400+0", 0),
    # Mythopoeic award for adult literature
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?401+0", 0),
    # Mythopoeic Fantasy Award for Young Adult Literature
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?1110+0", 0),
    # Mythopoeic Fantasy Award for Children's Literature
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?402+0", 0),


    ### Nebula awards
    # Nebulea awards, best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?413+0", 0),
    # Nebula awards, best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?415+0", 2),
    # Nebula awards, best novelette
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?414+0", 1),
    # Nebula awards, best short story
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?418+0", 1),
    # Andre Norton Nebula award for middle grade and young adult
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?1029+0", 0),

    ### Norton
    # Norton award for best young adult science fiction or fantasy
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?546+0", 0),

    ### Philip K. Dick award
    # Best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?423+0", 0),

    ### Premio Ignotus
    # Best foreign novel
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?748+0', 0),
    # Best Foreign Story
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?749+0', 1),
    # Best novel
    ('https://www.isfdb.org/cgi-bin/award_category.cgi?745+0', 0),

    ### Retro Hugo
    # Best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?439+0", 0),
    # Best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?441+0", 2),
    # Best novelette
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?440+0", 1),
    # Best short story
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?446+0", 1),

    ### Shirley Jackson Award
    # Best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?612+0", 0),
    # Best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?613+0", 2),
    # Best novelette
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?614+0", 1),
    # Best short fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?615+0", 1),
    # Best collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?616+0", 0),
    # Best anthology
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?617+0", 0),

    ### Sidewise
    # Best long form alternative history
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?520+0", 0),
    # Best short form alternative history
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?521+0", 1),

    ### Theodore Sturgeon Award
    # Best short science fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?768+0", 1),

    ### World Fantasy Award
    # Best novel
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?532+0", 0),
    # Best long fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?667+0", 0),
    # Best novella
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?533+0", 2),
    # Best short fiction
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?534+0", 1),
    # Best collection
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?531+0", 0),
    # Best anthology
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?528+0", 0),
    # Best anthology/collection (old)
    ("https://www.isfdb.org/cgi-bin/award_category.cgi?529+0", 0),
]

categories = {}

def parse_award_page(page):
    url = page[0]
    item_type = ""
    if page[1] == 0:
        item_type = "Work"
    elif page[1] == 1:
        item_type = "Short story"
    elif page[1] == 2:
        item_type = "Both"

    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")

    category = ""
    award_type = ""
    # Get category and award
    for li in soup.find_all("li"):
        b = li.find("b")
        if b and "Award Category:" in b.get_text():
            sibling = b.next_sibling
            if sibling:
                category = sibling.strip().split("\n")[0].strip()
        elif b and "Award Type:" in b.get_text():
            a = b.find_next("a")  # Find the next <a> after the <b>
            if a:
                award_type = a.get_text(strip=True)
    results = []

    table = soup.find("table")
    if not table:
        print(f"No table found in {url}", file=sys.stderr)
        return results

    print(f"{award_type} - {category}")
    if category not in categories:
        categories[category] = [""]

    year = ""
    for row in table.find_all("tr"):
        th = row.find("th")
        if th:
            a = th.find("a")
            if a and re.search(r'\d{4}', a.get_text()):
                year = a.get_text(strip=True)
        else:
            tds = row.find_all("td")
            if len(tds) == 3:
                if 'translation of' in tds[1].get_text(strip=True).lower():
                    # Get contents of second <a> tag
                    title_tag = tds[1].find_all("a")[1]
                else:
                    title_tag = tds[1].find("a")
                author_tag = tds[2].find("a")

                title = title_tag.get_text(
                    strip=True) if title_tag else tds[1].get_text(strip=True)
                author = author_tag.get_text(
                    strip=True) if author_tag else tds[2].get_text(strip=True)

                results.append((year, award_type, category, title, author, item_type))
    if award_type == "Hugo Award":
        # Hugo award page is broken from 2017
        for th in table.find_all("th"):
            a = th.find("a")
            if a and re.search(r'\d{4}', a.get_text()):
                year = a.get_text(strip=True)
                if int(year) >= 2017:
                    # Read info
                    tds = th.find_all_next("td")
                    a = tds[1].find("a")
                    if a:
                        title = a.get_text(strip=True)
                    else:
                        title = tds[1].get_text(strip=True)
                    author = tds[2].get_text(strip=True)
                    results.append((year, award_type, category, title, author, item_type))
    return results


# Gather all data
all_data = []
for url in award_urls:
    try:
        all_data.extend(parse_award_page(url))
    except Exception as e:
        print(f"Error processing {url}: {e}", file=sys.stderr)

print ("\n".join(f'"{k}": "{v[0]}"' for k,v in categories.items()))

# Output to stdout as TSV
with open("awards.tsv", "w") as f:
    f.write("year\taward_type\taward_category\ttitle\tauthor\titem_type\n")
    for row in all_data:
        f.write("\t".join(row) + "\n")
