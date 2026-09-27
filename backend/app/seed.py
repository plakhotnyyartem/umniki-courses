"""Демо-данные. Запуск: python -m app.seed (из папки backend). Пересоздаёт базу с нуля!"""

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .migrations import run_migrations
from .models import Course, Enrollment, Lesson, LessonProgress, Question, User
from .security import hash_password

DEMO_PASSWORD = "demo12345"

USERS = [
    dict(name="Администратор", email="admin@example.com", role="admin", avatar="🛡️"),
    dict(name="Анна Сергеевна", email="anna@example.com", role="teacher", avatar="🦉"),
    dict(name="Игорь Петрович", email="igor@example.com", role="teacher", avatar="🧮"),
    dict(name="Маша", email="masha@example.com", role="student", age=9, avatar="🦄"),
    dict(name="Петя", email="petya@example.com", role="student", age=12, avatar="🚀"),
]

# (курс, [(урок, текст, [вопросы])]). Вопрос — кортеж (текст, варианты, индекс правильного)
# для выбора варианта или словарь {text, accepted, match_numeric?} для ввода ответа.
COURSES = [
    (
        dict(title="Animals & Colours", subject="english", min_age=6, max_age=9, cover="🐾", teacher="anna@example.com",
             description="Учим названия животных, цветов и считаем до десяти на английском. Весёлые картинки и короткие уроки."),
        [
            ("Colours — цвета",
             "# Какого цвета?\n\nЗапомни главные цвета:\n\n- **red** — красный 🍎\n- **yellow** — жёлтый 🌞\n- **green** — зелёный 🐸\n- **blue** — синий 🐳\n\nСпроси друга: *What colour is it?* — Какого это цвета?\nОтвет: *It is red!*",
             [("Как по-английски «зелёный»?", ["red", "green", "blue"], 1),
              ("🍎 What colour is it?", ["It is yellow", "It is blue", "It is red"], 2),
              ("Что значит **blue**?", ["синий", "жёлтый", "белый"], 0),
              {"text": "Переведи на английский: «красный»", "accepted": ["red"]}]),
            ("Animals — животные",
             "# На ферме\n\n- **a cat** — кошка 🐱\n- **a dog** — собака 🐶\n- **a cow** — корова 🐮\n- **a horse** — лошадь 🐴\n\nЧтобы сказать, что у тебя есть питомец: *I have got a cat.*",
             [("Кто говорит «Woof»? 🐶", ["a cat", "a dog", "a cow"], 1),
              ("Как сказать «у меня есть кошка»?", ["I have got a cat", "I am a cat", "It is cat"], 0)]),
            ("Numbers 1–10",
             "# Считаем!\n\none, two, three, four, five, six, seven, eight, nine, ten.\n\nПопробуй посчитать свои пальцы на английском ✋✋",
             [("Сколько это: **seven**?", ["6", "7", "8"], 1),
              ("Как по-английски 3?", ["three", "tree", "free"], 0),
              ("Что идёт после **nine**?", ["eight", "ten", "one"], 1),
              {"text": "Напиши по-английски словом число 4", "accepted": ["four"]}]),
        ],
    ),
    (
        dict(title="Present Simple за 5 шагов", subject="english", min_age=10, max_age=14, cover="🕐", teacher="anna@example.com",
             description="Разбираемся с самым частым временем в английском: утверждения, отрицания и вопросы."),
        [
            ("Что такое Present Simple",
             "# Когда используем\n\nPresent Simple описывает то, что происходит **регулярно** или является **фактом**.\n\n- *I play football every Sunday.*\n- *The sun rises in the east.*\n\nСлова-подсказки: **always, usually, often, every day**.",
             [("Какое предложение в Present Simple?", ["I am playing now", "I play every day", "I played yesterday"], 1),
              ("Какое слово — подсказка Present Simple?", ["yesterday", "now", "usually"], 2)]),
            ("Окончание -s",
             "# He, she, it\n\nС **he / she / it** к глаголу добавляем **-s** или **-es**:\n\n- *She reads.*\n- *He watches TV.*\n- *It goes.*",
             [("Выбери правильный вариант: She ___ books.", ["read", "reads", "reading"], 1),
              ("He ___ TV every evening.", ["watchs", "watch", "watches"], 2),
              {"text": "Вставь глагол в нужной форме: She ___ (go) to school every day.", "accepted": ["goes"]}]),
        ],
    ),
    (
        dict(title="Таблица умножения", subject="math", min_age=7, max_age=10, cover="✖️", teacher="igor@example.com",
             description="Учим таблицу умножения с хитростями и мини-тестами. Больше не придётся зубрить!"),
        [
            ("Умножение на 2 и на 5",
             "# Хитрость для 2\n\nУмножить на 2 — значит **сложить число с самим собой**: 7 × 2 = 7 + 7 = 14.\n\n# Хитрость для 5\n\nОтветы при умножении на 5 всегда заканчиваются на **0 или 5**.",
             [("6 × 2 = ?", ["10", "12", "14"], 1),
              ("5 × 7 = ?", ["35", "30", "40"], 0),
              ("Какое число может быть ответом при умножении на 5?", ["42", "45", "44"], 1),
              {"text": "8 × 5 = ?", "accepted": ["40"]}]),
            ("Умножение на 9 — на пальцах",
             "# Фокус с пальцами\n\nПоложи обе руки на стол. Чтобы умножить 9 на 4, загни **четвёртый** палец слева.\n\nСлева осталось 3 пальца, справа — 6. Ответ: **36**!",
             [("9 × 3 = ?", ["27", "28", "36"], 0),
              ("9 × 6 = ?", ["45", "54", "56"], 1),
              {"text": "9 × 8 = ?", "accepted": ["72"]}]),
        ],
    ),
    (
        dict(title="Дроби — это просто", subject="math", min_age=10, max_age=13, cover="🍕", teacher="igor@example.com",
             description="Разбираемся с дробями на примере пиццы: что такое числитель и знаменатель, как сравнивать и складывать."),
        [
            ("Что такое дробь",
             "# Делим пиццу 🍕\n\nЕсли пиццу разрезали на **8** кусков и ты съел **3**, то ты съел **3/8** пиццы.\n\n- Верхнее число — **числитель** (сколько взяли)\n- Нижнее число — **знаменатель** (на сколько частей делили)",
             [("В дроби 3/8 знаменатель равен…", ["3", "8", "11"], 1),
              ("Пиццу разрезали на 4 части, съели 1. Какая часть съедена?", ["1/4", "4/1", "1/3"], 0),
              {"text": "Из пиццы в 8 кусков съели 3. Какая часть осталась? Запиши дробью.", "accepted": ["5/8"]}]),
            ("Сравнение дробей",
             "# Одинаковый знаменатель\n\nЕсли знаменатели равны, больше та дробь, у которой **больше числитель**: 5/7 > 2/7.\n\n# Одинаковый числитель\n\nЕсли числители равны, больше та, у которой **меньше знаменатель**: 1/2 > 1/5 (половина пиццы больше пятой части!).",
             [("Что больше?", ["3/10", "7/10"], 1),
              ("Что больше?", ["1/3", "1/6"], 0),
              ("Сложи: 2/9 + 5/9 = ?", ["7/18", "7/9", "10/9"], 1),
              # match_numeric=False: иначе «2/4» засчиталось бы как равное 1/2
              {"text": "Сократи дробь 2/4", "accepted": ["1/2"], "match_numeric": False}]),
        ],
    ),
    (
        dict(title="Простые уравнения", subject="math", min_age=12, max_age=14, cover="⚖️", teacher="igor@example.com",
             description="Черновик: курс ещё готовится.", is_published=False),
        [("Что такое уравнение", "Уравнение — это равенство с неизвестным.", [])],
    ),
]


def make_question(q) -> Question:
    if isinstance(q, dict):
        return Question(kind="text", **q)
    text, options, correct = q
    return Question(kind="choice", text=text, options=options, correct_index=correct)


def load_demo_courses(db, teacher_password_hash: str) -> list[Course]:
    """Создаёт демо-преподавателей (если их ещё нет) и их курсы. Возвращает курсы по порядку COURSES."""
    teachers = {}
    for info in USERS:
        if info["role"] != "teacher":
            continue
        user = db.scalar(select(User).where(User.email == info["email"]))
        if user is None:
            user = User(password_hash=teacher_password_hash, **info)
            db.add(user)
        teachers[info["email"]] = user
    db.flush()

    courses = []
    for info, lessons in COURSES:
        info = dict(info)
        teacher = teachers[info.pop("teacher")]
        course = Course(teacher_id=teacher.id, is_published=info.pop("is_published", True), **info)
        for pos, (title, content, questions) in enumerate(lessons, start=1):
            lesson = Lesson(title=title, content=content, position=pos)
            lesson.questions = [make_question(q) for q in questions]
            for qpos, question in enumerate(lesson.questions, start=1):
                question.position = qpos
            course.lessons.append(lesson)
        db.add(course)
        courses.append(course)
    db.flush()
    return courses


def run() -> None:
    """Локальная разработка: пересоздаёт базу и заводит все демо-аккаунты с паролем DEMO_PASSWORD."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    run_migrations(engine)
    db = SessionLocal()
    pw = hash_password(DEMO_PASSWORD)
    # Всех заводим в порядке USERS, чтобы id были предсказуемыми; учителей load_demo_courses найдёт
    users = {u["email"]: User(password_hash=pw, **u) for u in USERS}
    db.add_all(users.values())
    db.flush()
    courses = load_demo_courses(db, pw)

    # Маша уже прошла первый урок английского
    masha = users["masha@example.com"]
    db.add_all([
        Enrollment(user_id=masha.id, course_id=courses[0].id),
        Enrollment(user_id=masha.id, course_id=courses[2].id),
        Enrollment(user_id=users["petya@example.com"].id, course_id=courses[3].id),
        LessonProgress(user_id=masha.id, lesson_id=courses[0].lessons[0].id, score=4, total=4),
    ])
    db.commit()
    db.close()
    print(f"Готово. Демо-аккаунты созданы, пароль у всех: {DEMO_PASSWORD}")
    for u in USERS:
        print(f"  {u['role']:8} {u['email']}")


if __name__ == "__main__":
    run()
