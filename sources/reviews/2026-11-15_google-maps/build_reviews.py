"""Собирает reviews.jsonl и скриншоты отдельных отзывов из выгрузок Google Карт.

Запуск из корня проекта:
    python -I sources/reviews/2026-11-15_google-maps/build_reviews.py

Что делает:
  - читает полные выгрузки raw/*_all-reviews.json (по одной на карточку);
  - отбирает записи: все отзывы с оценкой 1-3; отзывы 4-5 с конкретной претензией
    (список MIXED ниже, составлен после чтения всех текстов); отзывы любой оценки,
    где упомянуты животные в зале (дополнение координатора); отзывы со сведениями
    о вместимости (дополнение координатора);
  - тексты берёт из выгрузки без правок;
  - id записей закрепляет в id_map.json, чтобы они не менялись при пересборке;
  - режет скриншоты отзывов из снимков панели (screenshots/_tmp/state_<seq>.png)
    по координатам из raw/*_screenshot-states-*.json либо берёт готовые снимки
    элементов (screenshots/_tmp/<venue>_<sort>_<pos>.png).

Сырые копии только читаются как данные и не исполняются.
"""
import json
import re
import shutil
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SHOTS = HERE / "screenshots"
TMP = SHOTS / "_tmp"
CAPTURE_DATE = date(2026, 11, 15)
APPROX_NOTE = "дата приблизительная, отсчитана от даты фиксации (15.11.2026)"

# Карточки: файл полной выгрузки -> сведения о карточке.
VENUES = {
    "001_google-maps_amazonka_all-reviews.json": {
        "venue": "amazonka-mogilev",
        "key": "amazonka",
        "url": (
            "https://www.google.com/maps/place/%D0%90%D0%BC%D0%B0%D0%B7%D0%BE%D0%BD%D0%BA%D0%B0+"
            "%D0%A0%D0%B5%D1%81%D1%82%D0%BE%D0%B1%D0%B0%D1%80/@53.9011724,30.3394751,17z/"
            "data=!4m8!3m7!1s0x46d051542fa346d1:0x7a0c8910e0b3df00!8m2!3d53.9011724!4d30.3394751"
            "!9m1!1b1!16s%2Fg%2F11jzksx23x?hl=ru"
        ),
        # Готовые снимки элементов из первого прохода: файл состояния -> ключ сортировки.
        "element_shots": {
            "006_google-maps_amazonka_sort-newest.json": "newest",
            "007_google-maps_amazonka_sort-lowest.json": "lowest",
            "008_google-maps_amazonka_sort-relevant.json": "relevant",
            "009_google-maps_amazonka_sort-highest.json": "highest",
        },
    },
    "025_google-maps_amazonka-minsk_all-reviews.json": {
        "venue": "amazonka-minsk",
        "key": "amazonka-minsk",
        "url": (
            "https://www.google.com/maps/place/%D0%90%D0%BC%D0%B0%D0%B7%D0%BE%D0%BD%D0%BA%D0%B0+"
            "%D1%80%D0%B5%D1%81%D1%82%D0%BE%D0%B1%D0%B0%D1%80/@53.897173,27.5555726,17z/"
            "data=!4m8!3m7!1s0x46dbcfe4c92789db:0x1f4d8821e0b4246d!8m2!3d53.897173!4d27.5555726"
            "!9m1!1b1!16s%2Fg%2F11mslx7wdq?hl=ru"
        ),
        "neg": {
            "Iryna Komar": (["service", "billing"], "negative",
                            "В тексте названа дата: 25 августа; вместо сдачи около 30 рублей предложили 18."),
            "Анна Моисеева": (["booking-events", "service"], "negative",
                              "В тексте названа дата: 30.08.2026; «при свободных 10 столах, сказали, что все забронировано»."),
            "Виктория": (["food-quality"], "negative", ""),
            "Ксения Дирко": (["booking-events", "service"], "negative",
                             "В тексте: бронь на 28 августа, «ожидание по кухне 2-3 часа»."),
            "Олеся Исаева": (["service", "receipt", "billing"], "negative",
                             "В тексте: «промокод не приняли, так как не было терминала. Предложили рассчитаться только наличными»."),
            "YC": (["service", "billing", "food-quality"], "negative",
                   "В тексте: от напитка отказалась, «но при этом меня заставили за него заплатить»."),
            "Кристина Щербо": (["delivery", "food-quality"], "negative", "В тексте: «рис сырой», «не могу вернуть деньги»."),
            "Диана Переломец": (["booking-events", "service"], "negative", ""),
            "Алиса": (["premises-building", "service", "food-quality"], "negative",
                      "В тексте: «Лестница на входе неудобная, кирпичи разваливаются»; посадили на втором этаже."),
            "Николай Рудчик": (["food-quality"], "negative",
                               "В тексте названа дата: 09 03; бульон «не свежим кислым». Ответ подписан «Руководство Амазонки»."),
            "max protasov": (["food-quality", "service"], "negative", ""),
        },
        "mixed": {
            "rakshi biktash": (["service"], "mixed", "Претензия: «Очень долгое ожидание»."),
            "Gop Lop": (["premises-building"], "mixed",
                        "Претензия в анкетном поле «Доступность для колясочников»: «Лестница, пандуса нет. И спуска тоже»."),
        },
    },
}

# Фото, которых нет в панели отзыва (скрыты за плиткой «+N»); ссылки получены в просмотрщике Google Карт.
HIDDEN_PHOTOS = {
    "Ксения Белова": [
        "https://lh3.googleusercontent.com/grass-cs/AABkmLePwCmPcvSnUaOm56UEsD2U4lQU6rVP6LG1_XhDVjU4F-6FSaPUNS8tRK6cbaD4Vye2ppddK-Uq3_Okov4uaryhBKhPJBvjpCpl4ZEJsY-mkOEGKjmJN1VCw0nafkJl-4B6v2fm48hDSCUw=k-no",
        "https://lh3.googleusercontent.com/grass-cs/AABkmLc6LoQ4B98WGy4GOQM5N6d0mEr1DHjf2nWjlnLPNYixQImWu0B_txVRIKWNvAHdZtHKUTyUxX7F_2Dy9mpA3aVN67T6AVU9ZAM-HUqsTCONOBGzcu1cPXXuCtgih82X0WJfwWW-nOt4veU=k-no",
        "https://lh3.googleusercontent.com/grass-cs/AABkmLcfemUxp42CfGdBvE0PVl0wLDRlwQCztGLR48BIlJhb8lpVgUgsdooTbiomANRuHa4RvYG0dQQdtQM5P908Xa2VN-oUvRn6BWl3VgpvxBDWpXzlJNyRd5zFItxWLTOWqO2U2gOJqKLbsQM9=k-no",
    ],
    "Анастасия Капуза": [
        "https://lh3.googleusercontent.com/grass-cs/AABkmLciyraXrxGR2-n8lwqjaXY7eJWFt9M2mXBcu2MBfBLs6aO54dnNdrI_KHxl8nuCgBMngJqTSalPEJ_aKnGCH2MWdLYe4OkZc9Xh4TqRhus431dwmJ3W64XWx4d9GeHhL6ozhyhg=k-no",
        "https://lh3.googleusercontent.com/grass-cs/AABkmLf7IfhX-eaweW8rm_rcF9Lq43YWuSrHfk_DW_wOHdBoMC1OUI-GpTVNcGrlbCnPeNT-912MA7wzf7qZk_Kxup3pK7ncSyJh31xxM7uZFWMLd6iAqSsRlkVQsVjIDzATROXfEHEr=k-no",
        "https://lh3.googleusercontent.com/grass-cs/AABkmLcEwY4-62_iWpqWLmv1Z2Vv4ZWLxv4nPeZG4VuWExRwr9u3uowbSJhNzWMD_bT_Dj8Oe7j5XDfWjgiPJhZoZjVxzWR6tXo-MYzeAxwqdi9IExQVHQB1eUMcV_H-MxPx4SHBFtAZ=k-no",
        "https://lh3.googleusercontent.com/grass-cs/AABkmLeJZq1u3LhoK6sBaW_qoRc6WAsKW2gK3aUZk8_Q64TIj5xjpKyemhXS1QACb46u1a9E2ynndtLajfOWLpqQQefv-fHTtLfhjA3MZJOGYJUFuxf-7DEYsxUjzbpjQanpDotaUE8=k-no",
    ],
}

# Месяц публикации приложенных фото по подписи в просмотрщике Google Карт («Фото – сент. 2026 г.»).
# Фото публикуется вместе с отзывом, поэтому месяц отзыва уточняется по нему.
PHOTO_PUBLISHED = {
    "Голубцова Алина": ("2025-06", "июнь 2025 г."),
    "kilroy": ("2024-01", "янв. 2024 г."),
    "Ксения Белова": ("2025-10", "окт. 2025 г."),
    "Анастасия Капуза": ("2023-11", "нояб. 2023 г."),
    "User": ("2026-09", "сент. 2026 г."),
    "марина": ("2025-06", "июнь 2025 г."),
    "Ульяна Сафонова": ("2026-09", "сент. 2026 г."),
    "Андрей Игнатов": ("2023-11", "нояб. 2023 г."),
    "Илья Белый": ("2026-09", "сент. 2026 г."),
    "Елена Гвоздева": ("2025-11", "нояб. 2025 г."),
}

# Темы для отзывов «Амазонки» с оценкой 1-3: автор -> (темы, тональность, пояснение).
# Ключ — имя автора и первые символы текста (для проверки, что речь о том же отзыве).
NEG = {
    "Андрей «Shadow» Тарасов": (["booking-events", "service"], "negative", ""),
    "Виктор Волковец": (["food-quality"], "negative", ""),
    "alya alya": (["service", "food-quality"], "negative", ""),
    "Xloa Cat": (["service", "other"], "negative", "В тексте: «посадили на сломанный диван»."),
    "Катя Иванова": (["sanitary", "food-quality", "service", "billing", "receipt"], "negative",
                     "В тексте: тараканы, туалет, запах от стаканов; «сказали оплачивать перевод с комиссией»."),
    "лиза": (["delivery", "food-quality"], "negative", "В тексте названа дата заказа: 14 октября."),
    "Юми Огава": (["booking-events", "service"], "negative", ""),
    "Olga Shpakova": (["sanitary", "service"], "negative", "В тексте: «наличие тараканов из-за жил.фонда»."),
    "Alesia Luzhankova": (["sanitary", "service", "food-quality"], "negative",
                          "В тексте: «еда для ваших рептилий ползает в зале по полу»."),
    "Анастасия Мельникова": (["billing", "alcohol", "food-quality", "service"], "negative",
                             "В тексте: коньяк 50 рублей, «а в чеке 65»; вес порций."),
    "Екатерина Романова": (["delivery", "food-quality"], "negative", ""),
    "Stani Dvorzheckiy": (["service"], "negative", ""),
    "Василий Кутепов": (["delivery"], "negative", ""),
    "Kaka Sasha": (["delivery"], "negative", ""),
    "Карина Бельская": (["service"], "negative", ""),
    "Ксения Галецкая": (["food-poisoning"], "negative",
                        "Текст на странице оканчивается многоточием, кнопки «Ещё» у отзыва нет; записан как показан."),
    "Gang": (["hookah-smoking", "fire-safety", "service"], "negative",
             "В тексте: угли от кальяна выбросили в пластиковую урну с пакетом, запах гари."),
    "НАТАЛЬЯ КОЗЛОВА": (["service", "food-quality", "booking-events", "premises-building"], "negative",
                        "В тексте названа дата посещения: 26.01.24; «два раза выключался полностью свет»."),
    "Mad Mak": (["booking-events", "service", "delivery"], "negative", "В тексте: «Зачем расширять само заведение…»."),
    "Олег Кондратчик": (["food-quality", "service"], "negative", ""),
    "Владимир": (["delivery", "food-quality"], "negative", ""),
    "Денис Астапенко": (["sanitary", "service", "food-quality", "alcohol", "billing"], "negative",
                        "В тексте: в туалете нет мыла; в чек включили десерты и пиво, от которых отказались."),
    "The Gauthier": (["service", "food-quality"], "negative", ""),
    "Алина Савченко": (["delivery"], "negative", ""),
    "Александра Розенталь": (["booking-events", "service", "food-quality", "alcohol", "premises-building"], "negative", ""),
    "Вероника Капаева": (["service", "food-quality", "hookah-smoking"], "negative", ""),
    "Ivan Akulenka": (["alcohol", "service", "receipt"], "negative",
                      "В тексте: «Чек не принесли, сумму на словах сказали, заплатил»; бурбон «либо палёный, либо разбавлен»."),
    "Kira Hudzen": (["food-quality"], "negative",
                    "Отзыв размещён в карточке могилёвской «Амазонки», но автор пишет о заведении «Амазонка рестобар» "
                    "в Орше на ул. Островской; к какому заведению относится — неясно."),
    "Артём Авхачев": (["service"], "negative", ""),
    "ирина левкович": (["food-quality", "service"], "negative", ""),
    "Андрей Игнатов": (["sanitary", "food-quality", "service"], "negative",
                       "В тексте: «Попалась железка в блюде», «столы грязные»."),
    "Полина Крупенько": (["service", "premises-building"], "negative", "В тексте: «отвратительно пахнет гарелым»."),
    "Mihail Zubr": (["service", "food-quality", "alcohol"], "negative", ""),
    "Карина Пролейчик": (["food-quality", "service"], "negative", "В тексте названа дата: 29.06 (год не указан)."),
    "Вероника Грысимова": (["delivery"], "negative", ""),
    "robe li": (["service"], "negative", ""),
    "Кирилл Кутузов": (["booking-events", "service"], "negative", ""),
    "Nastya Meow": (["service"], "negative", ""),
    "Стас Цофнас": (["service", "food-quality"], "negative", ""),
    "Иван Чеберак": (["service", "food-quality", "billing"], "negative",
                     "В тексте: фисташки предложили заменить арахисом «без изменения цены»; отказ позвать администратора."),
    "Нейм": (["service", "food-quality"], "negative", ""),
    "Ульяна Сафонова": (["sanitary", "service", "food-quality", "booking-events"], "negative",
                        "В тексте: тараканы на полу, стене и на краю тарелки; в туалете нет мыла, полотенец и бумаги. "
                        "К отзыву приложено видео 0:19; файл: media/google-maps-011/001_video.mp4 "
                        "(SHA-256 b20d7662bab04d5a1c30ec689bcc187801040c9ac198323ac2a74c0ad3ac7e72), кадры: "
                        "media_frames/google-maps-011/. На видео стена из реек у стола, на 9–12 секундах на рейке видно "
                        "тёмное насекомое; речи в звуковой дорожке нет (расшифровка пустая)."),
    "Алина Воднева": (["sanitary", "service"], "negative", "В тексте: «несколько тараканов»."),
    "A": (["food-poisoning", "service", "food-quality"], "negative", "В тексте: «спустя время ещё и животы заболели»."),
    "Татьяна Алесич": (["sanitary", "food-quality", "service"], "negative",
                       "В тексте: часть еды «не доготовлена и сырая»; «Рептилии в таких вонючих домиках. Какашки везде»."),
    "Дарья Масейкира": (["service"], "negative", ""),
    "Илья Белый": (["sanitary", "hookah-smoking", "food-quality", "service"], "negative",
                   "Подписи автора к четырём фото (видны в просмотрщике Google Карт): «грязный мундштук», «грязный стакан», "
                   "«грязный кальян», «грязные тарелки». Скриншоты: screenshots/amazonka_photo-r069-1.png … r069-4.png."),
    "Ирина Максимова": (["sanitary", "service"], "mixed",
                        "В тексте: состояние уборной; «в зале было максимум человек 10 на 3 стола»; "
                        "«время 23.30, заведение работает до 5 утра»."),
    "Марина Дайнеко": (["service", "hookah-smoking", "minors"], "mixed",
                       "В тексте: «нет отдельного зала для курения кальяна, учитывая, что в кафе приходят с детьми»."),
}

# Отзывы с оценкой 4-5, где есть конкретная претензия (прочитаны все тексты 4-5).
MIXED = {
    "Anastasiya Vazniuk": (["food-quality"], "mixed", "Претензия: суп «очень жирный и немного безвкусный»."),
    "Ксения Белова": (["premises-building"], "mixed", "Претензия: «не хватило кондиционера (было жарковато)»."),
    "Артур Арутюнов": (["premises-building"], "mixed",
                       "Претензия: «Немного не хватает освещения». Упомянута «зона на улице»."),
    "Анастасия Капуза": (["other"], "mixed", "Претензия: «Единственный минус это большая загруженность в зале»."),
    "G _ T": (["other"], "mixed", "Претензия: «не все террариумы с питомцами и их не так много как хотелось бы»."),
    "Анастасия Хокинз": (["service"], "mixed", "Претензия: «Почаще бы официанты вспоминали о том, что сидит столик»."),
    "Crazy Violet": (["food-quality"], "mixed", "Замечание о слишком сладких коктейлях с сиропом; еду принесли через полчаса."),
    "Karina Sav": (["premises-building", "booking-events"], "mixed",
                   "Претензия: «заведение не большое, в выходной день очень сложно попасть»."),
}

# Отзывы со сведениями о залах и числе людей (дополнение координатора «Вместимость»).
CAPACITY = {
    "Ирина Максимова": "«в зале было максимум человек 10 на 3 стола с учетом нас двоих»",
    "Юми Огава": "«весь 1 зал был пустым кроме 1 столика»",
    "Татьяна Алесич": "«кроме нас был занят только 1 столик»",
    "Марина Дайнеко": "«нет отдельного зала для курения кальяна»",
    "Анастасия Капуза": "«большая загруженность в зале», «столик лучше заказывать заранее»",
    "Karina Sav": "«заведение не большое, в выходной день очень сложно попасть»",
    "Mad Mak": "«Зачем расширять само заведение»",
    "Артур Арутюнов": "«Есть зона на улице , где можно с собаками»",
    "марина": "анкетное поле «Тип мест — Обеденный зал, Бар, Дворик или терраса, Места за барной стойкой»",
    "Александра Розенталь": "«зал полупустой»",
    "A": "«Ожидание еды долгое при пустом зале»",
    "Карина Пролейчик": "«посадка была далеко не полная»",
    "Ксения Белова": "«при полной посадке»",
    "Олег Кондратчик": "«маты из кухни на весь зал»",
}

# Слова о животных (дополнение координатора «Животные в зале»).
ANIMAL_RE = re.compile(
    r"(\bзме[яйиюеё]|\bпитон|\bудав(?:а|ы|ов|ом|у|е)?\b|\bигуан|\bящер|хамелеон|\bгекк?он|черепах|рептили|террариум|"
    r"аквариум|\bпаук|\bсверч|\bмыш(?:ь|и|ей|ам|ами|ах|ка|ки|ку|ек)\b|\bхомяк|\bхомяч|\bживотн|\bзвер[а-яё]*|"
    r"зоопарк|живой уголок|\bкорм(?:лени[а-я]*|ят|ить|а|у|ом)?\b|\bагам|\bбелочк|\bпитом[а-я]+|\bобитател|"
    r"\bжител[а-я]*|\bдомик|snake|python|lizard|iguana|reptile|terrarium|gecko|chameleon|\banimals?\b)",
    re.IGNORECASE,
)
# Отзывы, где автор жалуется на животных (запах, грязь, близость к еде) -> тема sanitary.
ANIMAL_SANITARY = {"Alesia Luzhankova", "Татьяна Алесич"}

REL_RE = [
    (re.compile(r"^(\d+) (?:час|часа|часов) назад$"), "hours"),
    (re.compile(r"^час назад$"), "hours1"),
    (re.compile(r"^(\d+) (?:минуту|минуты|минут) назад$"), "minutes"),
    (re.compile(r"^вчера$"), "yesterday"),
    (re.compile(r"^(\d+) (?:день|дня|дней) назад$"), "days"),
    (re.compile(r"^неделю назад$"), "week1"),
    (re.compile(r"^(\d+) (?:неделю|недели|недель) назад$"), "weeks"),
    (re.compile(r"^месяц назад$"), "month1"),
    (re.compile(r"^(\d+) (?:месяц|месяца|месяцев) назад$"), "months"),
    (re.compile(r"^год назад$"), "year1"),
    (re.compile(r"^(\d+) (?:год|года|лет) назад$"), "years"),
]


def approx_iso(shown):
    """Приблизительная дата по относительной подписи: до месяца или года."""
    if not shown:
        return None
    text = shown.strip().lower()
    for pattern, kind in REL_RE:
        match = pattern.match(text)
        if not match:
            continue
        number = int(match.group(1)) if match.groups() else 1
        ordinal = CAPTURE_DATE.toordinal()
        if kind in ("hours", "hours1", "minutes"):
            day = date.fromordinal(ordinal - (1 if kind == "hours" and number >= 12 else 0))
            return f"{day.year:04d}-{day.month:02d}"
        if kind == "yesterday":
            day = date.fromordinal(ordinal - 1)
            return f"{day.year:04d}-{day.month:02d}"
        if kind == "days":
            day = date.fromordinal(ordinal - number)
            return f"{day.year:04d}-{day.month:02d}"
        if kind in ("week1", "weeks"):
            day = date.fromordinal(ordinal - 7 * number)
            return f"{day.year:04d}-{day.month:02d}"
        if kind in ("month1", "months"):
            months = CAPTURE_DATE.year * 12 + (CAPTURE_DATE.month - 1) - number
            return f"{months // 12:04d}-{months % 12 + 1:02d}"
        if kind in ("year1", "years"):
            return f"{CAPTURE_DATE.year - number:04d}"
    return None


def nbsp(text):
    return text.replace(" ", " ") if isinstance(text, str) else text


def attr_lines(structured):
    return [": ".join(block) if len(block) > 1 else block[0] for block in structured]


def media_list(review, author, is_mogilev):
    """Прямая ссылка идёт первой (так её берёт tools/media_download.py), пояснение — после неё."""
    items = []
    for photo in review.get("photos") or []:
        aria = photo.get("aria") or ""
        more = re.match(r"^Ещё (\d+) фото", aria)
        url = photo.get("thumb_url")
        if aria == "Видео":
            items.append(f"{url} — заставка видео {photo.get('overlay_text') or ''}; само видео получают в просмотрщике Google Карт".replace("  ", " "))
        elif more:
            items.append(f"{url} — фото из отзыва; за этой плиткой в панели скрыто ещё {int(more.group(1)) - 1} фото")
        elif re.match(r"^Фото \d", aria):
            items.append(f"{url} — фото из отзыва")
        else:
            items.append(f"{url} — фото из отзыва, подпись автора: «{aria}»")
    if is_mogilev:
        for url in HIDDEN_PHOTOS.get(author, []):
            items.append(f"{url} — фото из отзыва, скрытое за плиткой «+N»; ссылка получена в просмотрщике Google Карт")
    return items


def load_id_map():
    path = HERE / "id_map.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def animal_hits(review):
    hits = []
    text = review.get("text") or ""
    reply = (review.get("reply") or {}).get("text") or ""
    if ANIMAL_RE.search(text):
        hits.append("в тексте отзыва")
    if ANIMAL_RE.search(reply):
        hits.append("в ответе владельца")
    for block in review.get("structured") or []:
        if ANIMAL_RE.search(" ".join(block)):
            hits.append("в анкетном поле")
            break
    return hits


def build_venue(raw_name, info, id_map, records, shot_sources):
    dump = json.loads((RAW / raw_name).read_text(encoding="utf-8"))
    selected = []
    for review in dump["reviews"]:
        author = nbsp(review["author"])
        rating = review["rating"]
        topics, sentiment, extra = None, None, ""
        if rating is not None and rating <= 3:
            if info["venue"] == "amazonka-mogilev" and author in NEG:
                topics, sentiment, extra = NEG[author]
            else:
                topics, sentiment, extra = info.get("neg", {}).get(author, ([], "negative", ""))
        elif info["venue"] == "amazonka-mogilev" and author in MIXED:
            topics, sentiment, extra = MIXED[author]
        elif author in info.get("mixed", {}):
            topics, sentiment, extra = info["mixed"][author]
        animals = animal_hits(review) if info["venue"] == "amazonka-mogilev" else []
        capacity = CAPACITY.get(author) if info["venue"] == "amazonka-mogilev" else None
        if topics is None and not animals and not capacity:
            continue
        reasons = []
        if topics is None:
            topics, sentiment = [], "positive"
            reasons.append("положительный отзыв; записан только из-за сведений, запрошенных дополнительно")
        topics = list(topics)
        if animals:
            wanted = "sanitary" if author in ANIMAL_SANITARY else "other"
            if wanted not in topics:
                topics.append(wanted)
        if capacity and "premises-building" not in topics and sentiment == "positive":
            topics.append("premises-building")
        selected.append((review, author, topics, sentiment, extra, animals, capacity, reasons))

    for review, author, topics, sentiment, extra, animals, capacity, reasons in selected:
        rid = review["review_id"]
        if rid not in id_map:
            id_map[rid] = f"google-maps-{len(id_map) + 1:03d}"
        record_id = id_map[rid]
        text = review["text"]
        notes = []
        structured = attr_lines(review.get("structured") or [])
        if not text:
            text = "\n".join(structured) if structured else (review.get("rating_label") or "")
            notes.append("Отзыв без текста: в поле text — оценки и анкетные поля, как они показаны под оценкой.")
            if not topics:
                low = []
                for line in structured:
                    match = re.match(r"^(Еда|Сервис|Атмосфера): (\d)$", line)
                    if match and int(match.group(2)) <= 2:
                        low.append({"Еда": "food-quality", "Сервис": "service", "Атмосфера": "other"}[match.group(1)])
                topics = low
                if low:
                    notes.append("Темы проставлены по подоценкам 1–2.")
        elif structured:
            notes.append("Анкетные поля под текстом: " + "; ".join(structured) + ".")
        shown = nbsp(review.get("date_shown"))
        iso = approx_iso(shown)
        photo_date = PHOTO_PUBLISHED.get(author) if info["venue"] == "amazonka-mogilev" else None
        if photo_date:
            iso = photo_date[0]
            notes.append(f"дата приблизительная: месяц взят из подписи к приложенному фото в просмотрщике Google Карт "
                         f"(«Фото – {photo_date[1]}»), относительная дата отсчитана от даты фиксации (15.11.2026).")
        elif iso:
            notes.append(APPROX_NOTE + ".")
        if review.get("badge"):
            notes.append(f"Метка на странице: «{review['badge']}».")
        reply = review.get("reply")
        reply_text = reply["text"] if reply and reply.get("text") else None
        if reply:
            notes.append(f"{reply.get('label') or 'Ответ владельца'}: {nbsp(reply.get('date_shown'))}.")
        if animals:
            notes.append("животные в зале (упоминание " + ", ".join(animals) + ").")
        if capacity:
            notes.append("Вместимость/залы: " + capacity + ".")
        if extra:
            notes.append(extra)
        notes.extend(reasons)
        if review.get("translate_controls"):
            notes.append("Текст на языке оригинала (на странице есть кнопка перевода).")
        notes.append(f"review_id: {rid}")
        venue = info["venue"]
        if author == "Kira Hudzen" and venue == "amazonka-mogilev":
            venue = "unclear"
        first_seen = review["seen_in"][0]["captured_at"]
        captured = first_seen.replace("Z", "+00:00")
        captured = re.sub(r"\.\d+\+", "+", captured)
        records.append({
            "id": record_id,
            "venue": venue,
            "platform": "google-maps",
            "kind": "review",
            "url": info["url"],
            "author": author,
            "date_published": shown,
            "date_iso": iso,
            "rating": review["rating"],
            "text": text,
            "reply": reply_text,
            "sentiment": sentiment,
            "topics": topics,
            "media": media_list(review, author, info["venue"] == "amazonka-mogilev"),
            "captured_at": captured,
            "raw_file": f"raw/{raw_name}",
            "screenshot": None,
            "access": "public",
            "status": "verified-raw",
            "notes": " ".join(notes),
        })
        shot_sources[record_id] = (info, rid)


def collect_shot_index(info):
    """review_id -> ('element', путь) или ('crop', путь снимка панели, прямоугольник, dpr)."""
    index = {}
    for state_name, sort_key in info.get("element_shots", {}).items():
        path = RAW / state_name
        if not path.is_file():
            continue
        state = json.loads(path.read_text(encoding="utf-8"))
        for review in state["reviews"]:
            shot = TMP / f"{info['key']}_{sort_key}_{review['position']}.png"
            if shot.is_file():
                index.setdefault(review["review_id"], ("element", shot))
    for path in sorted(RAW.glob(f"*_{info['key']}_screenshot-states-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for state in data["states"]:
            shot = TMP / f"{info['key']}_state_{state['seq']}.png"
            if not shot.is_file():
                shot = TMP / f"state_{state['seq']}.png"
            if not shot.is_file():
                continue
            dpr = state["viewport"]["dpr"]
            for review in state["reviews"]:
                if review.get("rect"):
                    index.setdefault(review["review_id"], ("crop", shot, review["rect"], dpr))
    return index


def make_screenshots(records, shot_sources):
    from PIL import Image

    cache = {}
    indexes = {}
    made = 0
    for record in records:
        info, rid = shot_sources[record["id"]]
        if info["key"] not in indexes:
            indexes[info["key"]] = collect_shot_index(info)
        source = indexes[info["key"]].get(rid)
        target = SHOTS / f"{record['id']}.png"
        if source is None:
            if target.is_file():
                record["screenshot"] = f"screenshots/{target.name}"
            continue
        if source[0] == "element":
            shutil.copyfile(source[1], target)
        else:
            _, shot, rect, dpr = source
            if shot not in cache:
                cache[shot] = Image.open(shot)
            image = cache[shot]
            box = (
                max(0, int(rect["x"] * dpr)),
                max(0, int(rect["y"] * dpr)),
                min(image.width, int((rect["x"] + rect["w"]) * dpr) + 1),
                min(image.height, int((rect["y"] + rect["h"]) * dpr) + 1),
            )
            image.crop(box).save(target)
        record["screenshot"] = f"screenshots/{target.name}"
        made += 1
    return made


def extra_records(id_map):
    """Записи не об отзывах: карточка «Смак.Бай» (заведение ещё не открыто, отзывов нет)."""
    out = []
    card = RAW / "016_google-maps_smak-by_card.json"
    if card.is_file():
        data = json.loads(card.read_text(encoding="utf-8"))
        key = "card:smak-by"
        if key not in id_map:
            id_map[key] = f"google-maps-{len(id_map) + 1:03d}"
        captured = re.sub(r"\.\d+Z$", "+00:00", data["captured_at"])
        out.append({
            "id": id_map[key],
            "venue": "smak-by",
            "platform": "google-maps",
            "kind": "other",
            "url": ("https://www.google.com/maps/place/%D0%A1%D0%BC%D0%B0%D0%BA.%D0%91%D0%B0%D0%B9+"
                    "%D0%91%D0%B5%D0%BB%D0%BE%D1%80%D1%83%D1%81%D1%81%D0%BA%D0%B0%D1%8F+%D0%BA%D1%83%D1%85%D0%BD%D1%8F/"
                    "data=!4m7!3m6!1s0x46d051bfde343e71:0xf6de0cf4ddb24d6f!8m2!3d53.9023959!4d30.3396666"
                    "!16s%2Fg%2F11p2ds2mpr!19sChIJcT403r9R0EYRb02y3fQM3vY?hl=ru"),
            "author": None,
            "date_published": None,
            "date_iso": None,
            "rating": None,
            "text": "Смак.Бай Белорусская кухня\nОткрытие: ноябрь",
            "reply": None,
            "sentiment": "neutral",
            "topics": ["ads-unlicensed"],
            "media": [],
            "captured_at": captured,
            "raw_file": "raw/016_google-maps_smak-by_card.json",
            "screenshot": "screenshots/smak-by_card.png",
            "access": "public",
            "status": "verified-raw",
            "notes": ("Карточка заведения на Google Картах, не отзыв. Категория «Семейный ресторан», адрес "
                      "«улица Будённого 13-64, Могилёв, Могилёвская область 212039, Беларусь», строка «Открытие: ноябрь», "
                      "«Указано, что владелец – женщина». Отзывов нет, часов работы, телефона и сайта нет. "
                      "В карточке 7 изображений от имени «Смак.Бай Белорусская кухня» с подписью «Фото – окт. 2026 г.»: "
                      "логотип и шесть изображений интерьера, по виду — дизайн-визуализации, а не снимки готового помещения "
                      "(скриншот: screenshots/smak-by_photos_gallery.png; список: raw/017_google-maps_smak-by_photos-list.json)."),
        })
    return out


def main():
    id_map = load_id_map()
    records = []
    shot_sources = {}
    for raw_name, info in VENUES.items():
        if (RAW / raw_name).is_file():
            build_venue(raw_name, info, id_map, records, shot_sources)
    made = make_screenshots(records, shot_sources)
    records.extend(extra_records(id_map))
    records.sort(key=lambda record: record["id"])
    (HERE / "id_map.json").write_text(json.dumps(id_map, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    with (HERE / "reviews.jsonl").open("w", encoding="utf-8", newline="\n") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
    with_shot = sum(1 for record in records if record["screenshot"])
    print(f"records={len(records)} screenshots_written={made} with_screenshot={with_shot}")


if __name__ == "__main__":
    main()
