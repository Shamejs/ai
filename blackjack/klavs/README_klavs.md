# Blackjack — Klāvs

Šī ir Klāva darba mape Blackjack bota uzdevumam.

`app.py` palaiž vietējo Blackjack galdu, kur `klavs_bot` spēlē pret
dīleri. Saskarne rāda running/true count, nākamo likmi, rokas punktus un bota
lēmuma pamatojumu. Publiskās kurpes audits rāda redzamo kāršu statistiku un
jaukšanas reižu skaitu; statistikas novirze nav pierādījums manipulācijai.
Dzīvajā gājienu žurnālā redzamas atklātās kārtis, dīlera gājieni un raunda
iznākums. Apakšējās pogas ļauj sākt raundu, palaist 10 roku demonstrāciju,
to apturēt vai atiestatīt galdu.

Palaišana no repozitorija saknes:

```powershell
python blackjack\klavs\app.py
```

Lai pārbaudītu `klavs_bot` pasniedzēja turnīrā, palaid turnīru no
repozitorija saknes. Turnīrs ielādē derīgos botus no Blackjack apakšmapēm.

```powershell
python blackjack\tournament.py
```

`bot.py` īsteno pasniedzēja API: `place_bet` un `decide_action`. Bots izmanto
Hi-Lo kāršu skaitīšanu no publiski redzamās vēstures un pamata stratēģiju,
kas ievēro dīlera apstāšanos pie 17, Blackjack 3:2 izmaksu un atļautās split/
double darbības. `place_bet` saņem atlikušās kavas, tāpēc bots nosaka arī
turnīra konfigurēto kavu skaitu; lēmuma laikā aprēķins ierēķina vienu slēpto
dīlera kārti kā nezināmu, nevis redzamu. Pie aptuveni 75% izspēlēto kāršu
turnīrs pats pārjauc kavu un atiestata vēsturi, tāpēc atiestatās arī skaits.
Likme pieaug tikai tad, ja true count norāda uz pozitīvu sagaidāmo priekšrocību
un pašreizējais bankroll atbalsta lielāku summu. Likmes griestus nosaka
ceturtdaļas Kelly aprēķins ar aptuvenu 0.5% priekšrocības izmaiņu uz true-count
punktu un 1.3 vienību rokas iznākuma dispersiju; skala tiek aprauta pie 200
žetoniem. Tas ir konservatīvāk par fiksētu bankroll slieksni un automātiski
samazina risku pēc zaudējumiem. Pie negatīva vai zema skaita bots paliek pie
minimālajiem 10 žetoniem un likmi nepalielina tikai tāpēc, ka zaudēja. Tā kā
minimālā likme ir 10, pie bankroll zem 10 spēlētājs tiek izslēgts, bet pie
maza bankroll minimālā likme joprojām var būt liela daļa no atlikuma.
Neparastas publisko kāršu proporcijas vai neiespējamas kārtis liek botam
samazināt likmi līdz minimumam un izlaist skaita novirzes, dubultošanu un dalīšanu.
Šāds statistikas brīdinājums nav pierādījums manipulācijai vai dīlera rīcībai.
Slēptā kārts un nākamās nejaušās kārtis nav zināmas, tāpēc neviena stratēģija
nevar garantēt perfektu katra raunda iznākumu; bots izvēlas labāko pieejamo
gājienu pēc publiskās informācijas un norādītajiem noteikumiem.
`game.py` un `app.py` veido vietējo demonstrāciju ar 4 kavu kopējo kurpi,
dīleri un likmēm.

Demonstrācija ir viena bota pret dīleri; pasniedzēja turnīrā boti dalīs vienu
kopēju kurpi un `history` ietvers arī citu botu atklātās kārtis.

Botu un spēles loģikas testi:

```powershell
python -m unittest discover -s blackjack\klavs -p "test_*.py" -v
```
