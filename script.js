const compatibilityForm = document.getElementById("compatibilityForm");
const loaderSection = document.getElementById("loaderSection");
const resultSection = document.getElementById("resultSection");
const progressBar = document.getElementById("progressBar");
const resultTitle = document.getElementById("resultTitle");
const resultSubtitle = document.getElementById("resultSubtitle");
const westernText = document.getElementById("westernText");
const chineseText = document.getElementById("chineseText");
const numerologyText = document.getElementById("numerologyText");
const bonusText = document.getElementById("bonusText");
const strengthsList = document.getElementById("strengthsList");
const growthList = document.getElementById("growthList");
const weeklyAdvice = document.getElementById("weeklyAdvice");
const conflictTip = document.getElementById("conflictTip");
const forecastTip = document.getElementById("forecastTip");
const funTip = document.getElementById("funTip");
const aspectsText = document.getElementById("aspectsText");
const vectorText = document.getElementById("vectorText");
const timelineText = document.getElementById("timelineText");
const dynamicsText = document.getElementById("dynamicsText");
const greenFlagsList = document.getElementById("greenFlagsList");
const redFlagsList = document.getElementById("redFlagsList");
const areasText = document.getElementById("areasText");
const bestDaysList = document.getElementById("bestDaysList");
const energyTrendChart = document.getElementById("energyTrendChart");
const shareBtn = document.getElementById("shareBtn");
const copyLinkBtn = document.getElementById("copyLinkBtn");
const printPdfBtn = document.getElementById("printPdfBtn");
const downloadPngBtn = document.getElementById("downloadPngBtn");
const expertBtn = document.getElementById("expertBtn");
const crmForm = document.getElementById("crmForm");
const crmStatus = document.getElementById("crmStatus");
const themeToggle = document.getElementById("themeToggle");

let chart;
let trendChart;
let latestResult;
/** Хэш вида #sovmestimost/oven-i-skorpion — добавляется к URL после расчёта и в «Поделиться». */
let compatibilityUrlHash = "";

const GEO_SEARCH_URL = "https://geocoding-api.open-meteo.com/v1/search";

const DEFAULT_PAGE_TITLE = "Калькулятор совместимости по дате рождения | MagicLove";
const DEFAULT_PAGE_DESC =
  "Узнайте совместимость в любви и браке. Бесплатный расчёт по знакам зодиака, нумерологии и китайскому гороскопу.";

const ZODIAC_SIGN_SLUG = {
  Овен: "oven",
  Телец: "telets",
  Близнецы: "bliznecy",
  Рак: "rak",
  Лев: "lev",
  Дева: "deva",
  Весы: "vesy",
  Скорпион: "skorpion",
  Стрелец: "strelec",
  Козерог: "kozerog",
  Водолей: "vodoley",
  Рыбы: "ryby",
};

/** Родительный падеж после «у» (у Козерога, у Рыб). */
const SIGN_RU_GENITIVE = {
  Овен: "Овна",
  Телец: "Тельца",
  Близнецы: "Близнецов",
  Рак: "Рака",
  Лев: "Льва",
  Дева: "Девы",
  Весы: "Весов",
  Скорпион: "Скорпиона",
  Стрелец: "Стрельца",
  Козерог: "Козерога",
  Водолей: "Водолея",
  Рыбы: "Рыб",
};

function signRuGenitive(nameRu) {
  const s = (nameRu || "").trim();
  return SIGN_RU_GENITIVE[s] || s;
}

const VALID_SIGN_SLUG_SET = new Set(Object.values(ZODIAC_SIGN_SLUG));

/** Даты середины знака (полдень в TZ формы → совпадает с логикой API): подстановка из хэша #sovmestimost/… */
const SLUG_SAMPLE_BIRTH = {
  oven: "2000-04-10",
  telets: "2000-05-10",
  bliznecy: "2000-06-10",
  rak: "2000-07-10",
  lev: "2000-08-10",
  deva: "2000-09-10",
  vesy: "2000-10-10",
  skorpion: "2000-11-10",
  strelec: "2000-12-10",
  kozerog: "2000-01-10",
  vodoley: "2000-02-10",
  ryby: "2000-03-10",
};

const RELATIONSHIP_LOCATIVE = {
  romance: "любви",
  friendship: "дружбе",
  business: "бизнесе",
};

/** Стихия по слагу знака (для всех 66 пар). */
const ZODIAC_ELEMENT_BY_SLUG = {
  oven: "Огонь",
  telets: "Земля",
  bliznecy: "Воздух",
  rak: "Вода",
  lev: "Огонь",
  deva: "Земля",
  vesy: "Воздух",
  skorpion: "Вода",
  strelec: "Огонь",
  kozerog: "Земля",
  vodoley: "Воздух",
  ryby: "Вода",
};

/** Краткая черта знака — уникальное второе предложение для каждой пары. */
const SIGN_TRAIT_BY_SLUG = {
  oven: "прямоту и инициативу",
  telets: "спокойствие и верность привычке",
  bliznecy: "любознательность и гибкость",
  rak: "заботу и чувство «своих»",
  lev: "щедрость и потребность в признании",
  deva: "аккуратность и стремление к порядку",
  vesy: "тонкость такта и поиск равновесия",
  skorpion: "глубину и накопление доверия",
  strelec: "оптимизм и жажду смысла",
  kozerog: "ответственность и долгосрочные цели",
  vodoley: "свободу взгляда и нестандартность",
  ryby: "эмпатию и воображение",
};

/** Ключ пары: два слага в лексикографическом порядке. */
function seoSlugPairKey(slug1, slug2) {
  if (!slug1 || !slug2) return "";
  return slug1 < slug2 ? `${slug1}-${slug2}` : `${slug2}-${slug1}`;
}

/**
 * «Ручные» абзацы для каждой из 66 неупорядоченных пар (без повтора имён в теле —
 * порядок в заголовке может совпадать с формой пользователя).
 */
const SEO_PAIR_HANDCRAFTED = {
  "bliznecy-deva":
    "Разговор как топливо и тяга к ясности: одному важно перебирать варианты, другому — доводить до аккуратного конца. Спор «кто прав» сменяется на пользу, если договориться о критериях «достаточно хорошо» и не подменять заботу занудством.",
  "bliznecy-kozerog":
    "Лёгкость на поверхности и серьёзность в глубине: пара умеет и шутить, и строить на годы вперёд. Риск — разный темп: одному нужны свежие стимулы, другому — понятные рамки; помогает совместный календарь и честное «сейчас не до идей».",
  "bliznecy-lev":
    "Сцена и сценарий: яркие истории, люди, впечатления — вместе легко сиять в компании. Сложнее тихие вечера без оценки «кто центр внимания»; близость крепнет, когда хвалят не только поступки, но и простое присутствие рядом.",
  "bliznecy-oven":
    "Импульс и любопытство в одном флаконе: стартуют быстро, обсуждают ещё быстрее. Выигрывают в проектах и поездках; острый угол — доводить начатое до конца и не превращать спор в соревнование кто громче.",
  "bliznecy-rak":
    "Слова лечат и ранят сильнее обычного: настроение одного мгновенно считывается другим. Хорошо получается уютные беседы и планы «на двоих»; важно называть потребность в тишине вслух, а не закрываться намёками.",
  "bliznecy-ryby":
    "Образы, музыка, ассоциации — мир чувств становится общим языком. Тонкая, почти художественная связь; чтобы не «утонуть» вдвоём, полезны якоря в реальности: сон, еда, прогулки без телефонов.",
  "bliznecy-skorpion":
    "Лёгкий тон и накопительная глубина: шутка для одного — проверка доверия для другого. Сила — в честности без драмы и в паузе перед язвительностью; тогда страсть не превращается в игру в «угадай мотив».",
  "bliznecy-strelec":
    "Философия за завтраком и спонтанные билеты: вдохновляют друг друга на смысл и движение. Минус — разброс фокуса; пара крепнет, когда находит одну-две общие цели и учится возвращаться к быту без уныния.",
  "bliznecy-telets":
    "Новизна натыкается на привычку: одному хочется смены декораций, другому — предсказуемости. Работает микс «пятница — сюрприз, воскресенье — дом»; спор о деньгах смягчается бюджетом «на эксперименты».",
  "bliznecy-vesy":
    "Двойной воздух: такт, юмор, светская хватка. Легко быть парой «все завидуют»; глубина растёт через уязвимые темы без зрителей и через маленькие обещания, которые выполняют в тишине.",
  "bliznecy-vodoley":
    "Идеи скачут, правила гнутся: разговор не иссякает ни ночью, ни в очереди. Риск — эмоциональная дистанция под видом свободы; тепло держится на ритуалах «мы» и на честном «мне сейчас важно внимание, не совет».",
  "deva-kozerog":
    "Две опоры здравого смысла: дисциплина, качество, долгая дистанция. Из минусов — суховатость и взаимные замечания; лекарство — похвала за усилия и совместный отдых, который не нужно «заслуживать идеальным отчётом».",
  "deva-lev":
    "Служение деталям и потребность в аплодисментах: один выстраивает фундамент, другой задаёт направление «света». Конфликт часто о форме критики; мягкая подача фактов и публичное «спасибо» возвращают игру в команду.",
  "deva-oven":
    "Точность встречает рывок: один тормозит лишнее, другой толкает вперёд. В паре зрят менеджмент и стартапы; злится друг на друга из-за темпа. Помогает чёткое разделение ролей и правило «сначала действие — потом правки».",
  "deva-rak":
    "Забота в быту и тонкие чувства: можно собрать очень тёплый дом. Опасность — «я знаю, как лучше» вместо слушания; доверие растёт, когда критика идёт после объятий, а не до них.",
  "deva-ryby":
    "Порядок и туман воображения: один приземляет мечты, другой смягчает жёсткость реальности. Красивый тандем «сервис + душа»; важно не подменять заботу контролем и оставлять место хаосу творчества.",
  "deva-skorpion":
    "Анализ и интуиция: вместе замечают то, что другие пропускают. Риск — взаимное копание в мотивах; сила — в совместной тайне и уважении к границам, без допроса «на чистоту» каждый вечер.",
  "deva-strelec":
    "Мелкий шрифт и широкий кадр: один видит риски, другой — горизонт. Учатся друг у друга смелости и аккуратности; спорят о смысле vs пользе — мирятся общим путеводителем ценностей, а не слайдами.",
  "deva-telets":
    "Две земли в быту: стабильность, вкус, терпение. Может стать чуть «скучновато» снаружи и очень надёжно внутри; оживляет совместные проекты с телом — сад, спорт, гости — не только списки дел.",
  "deva-vesy":
    "Такт и правка: хотят красиво и правильно одновременно. Хорошо в паре «приём гостей и идеальный сервис»; напряжение — избегание острых тем ради гладкости; честный короткий разговор лучше недельного холодного тона.",
  "deva-vodoley":
    "Система и исключение из правил: один любит проверенные методы, другой — ломать шаблоны. Интересно в науке, IT, соцпроектах; сближает уважение к чужой логике и запрет на сарказм про «бредовые идеи».",
  "kozerog-lev":
    "Статус, амбиции, публичный образ — общий язык. Трение — кто главный в стратегии; выигрывают, когда хвалят вклад друг друга перед третьими лицами и дома оставляют соревнование за порогом.",
  "kozerog-oven":
    "Цель и рывок: вместе пробивают стены, если договорились о правилах игры. Один даёт выдержку, другой — искру; спорят о поспешности vs осторожностью — лечится совместным дедлайном и правом на «стоп-день».",
  "kozerog-rak":
    "Дом как проект и дом как сердце: фундамент и тепло дополняют друг друга. Риск — сухие ответы на эмоциональные сигналы; близость растёт через маленькие ритуалы заботы без лекций о «правильных чувствах».",
  "kozerog-ryby":
    "Рамки и течение: один держит курс, другой напоминает, зачем вообще плыть. Глубокий союз, если Козерог не обесценивает «туманные» сны, а Рыбы не срывают сроки «по настроению» без предупреждения.",
  "kozerog-skorpion":
    "Мало слов — много подтекста: выносливость и контроль в одном пакете. Сила в общих долгих целях; опасность — молчаливые обиды; лечится расписанными check-in разговорами, даже если они короткие.",
  "kozerog-strelec":
    "Долгая дистанция и широкий жест: один строит, другой расширяет горизонт. Конфликт «скучно vs рискованно»; мирятся парой смелых поездок в год и чётким «фондом безопасности» на непредвиденное.",
  "kozerog-telets":
    "Две опоры: материальная база, традиции, терпение. Может казаться слишком серьёзно снаружи; внутри — редкая предсказуемость. Оживляет совместное «позволим себе» без чувства вины.",
  "kozerog-vesy":
    "Карьера и харизма, правила и обаяние. Хорошо в паре «переговоры и имидж»; напряжение — когда вежливость скрывает недосказанность; прямой короткий факт лучше красивой отсрочки.",
  "kozerog-vodoley":
    "Институт и реформатор: один ценит проверенное, другой тянет к будущему. Сильны в технологиях, бизнесе, науке; сближает общее дело вне дома и уважение к странности партнёра как к ресурсу, а не к багу.",
  "lev-oven":
    "Двойной огонь: щедрость, смелость, азарт. Легко зажечь зал и друг друга; сложнее тормозить и слушать усталость. Работает честное «мне нужен тихий вечер» без обид на охлаждение страсти.",
  "lev-rak":
    "Свет софитов и уют берега: один даёт гордость, другой — безопасность. Драма возможна из-за «недостаточно внимания»; лекарство — явные жесты признательности и разделение публичного и домашнего.",
  "lev-ryby":
    "Театр и подводный мир: внешняя яркость и тихая глубина. Один тянет в события, другой — к смыслу и тишине; красиво, когда Лев учится слушать намёки, а Рыбы — называть просьбы прямо.",
  "lev-skorpion":
    "Власть, страсть, ревность — на кончике языка. Магнетизм сильный; правила честности и личного пространства спасают от сцен. Хорошо работают совместные цели «мы против задачи», а не «я против тебя».",
  "lev-strelec":
    "Щедрость, оптимизм, любовь к широкому жесту: вместе легко вдохновляют окружение. Минус — забыть про мелочи и деньги; плюс — общий юмор и умение после авантюры спокойно разбирать последствия без поиска виноватого.",
  "lev-telets":
    "Корона и кухня: статус и комфорт, зрелище и вкус. Один хочет аплодисментов, другой — стабильности; мирятся бюджетом на «сияние» и честным признанием вклада тихого труда в тылу.",
  "lev-vesy":
    "Стиль, свет, социальные связи — пара «как из журнала». Риск — поверхностность и зависть снаружи; глубина — в разговорах без публики и в способности извиниться красиво и по-настоящему.",
  "lev-vodoley":
    "Личный бренд и коллективное будущее: яркость встречает идею. Интересно в медиа, ивентах, благотворительности; трение — когда свобода читается как равнодушие; лечится явными договорённостями о близости.",
  "oven-rak":
    "Прямолинейность и тонкая оболочка: слова режут сильнее, чем кажется. Сила — в защите «своих» и в быстром заглаживании; важно замедляться перед фразой и спрашивать «как тебе сейчас», а не только «что делать».",
  "oven-ryby":
    "Рывок и течение: один тянет в бой, другой смягчает углы интуицией. Романтика нежная и странная одновременно; спасает юмор и запрет на язвительность в усталость.",
  "oven-skorpion":
    "Искра и сжатие: страсть на высоких оборотах, мало посредников. Вместе пробивают стены; осторожность нужна с границами и ревностью — договорённость «что ок, а что нет» лучше любых проверок.",
  "oven-strelec":
    "Честность без лишней дипломатии и вера в горизонт: друзья по духу и по дороге. Риск — оба правы и оба громкие; мирятся совместным спортом, поездкой или проектом, где есть место двум капитанам по очереди.",
  "oven-telets":
    "Старт и тормоз: импульс натыкается на «давай подумаем». Зато из идей получаются вещи, если Овен уважает темп, а Телец — иногда отпускает контроль ради спонтанного «да».",
  "oven-vesy":
    "Такт vs прямота: один бьёт в лоб, другой оборачивает конфликт в диалог. Хорошо в паре «переговоры и дебаты»; важно не превращать обсуждение в вечный холодный тон — иногда нужен жест, а не аргумент.",
  "oven-vodoley":
    "Эксперимент и рывок: вместе открывают необычное и не ждут разрешения судьбы. Свобода ценится высоко; близость крепнет, когда «свобода» не означает «мне всё равно», а «я выбираю тебя снова каждый день».",
  "rak-ryby":
    "Два океана эмпатии: чувствуют комнату раньше слов. Красота — в тишине и заботе; риск — взаимное накручивание тревоги; спасает вынос разговоров на прогулку и один внешний якорь — друг, терапия, спорт.",
  "rak-skorpion":
    "Память чувств и память обид: глубина без дна. Доверие строится годами и ломается фразой; сила — в прямоте без шантажа и в праве на личное пространство без чувства измены.",
  "rak-strelec":
    "Дом и дорога: один цепляется за уют, другой за горизонт. Работает, когда путешествия планируются вместе, а возвращение домой — праздник, а не «отработка долга» перед свободой.",
  "rak-telets":
    "Классика «семья и стол»: надёжность, вкус, телесный комфорт. Мало драмы ради зрителей, много заботы по-настоящему; оживляет совместное «выйдем из дома», чтобы не застрять в плед-пледа.",
  "rak-vesy":
    "Настроение и такт: один колеблется внутри, другой сглаживает снаружи. Риск — недосказанность ради мира; лучше короткая честная беседа, чем вежливая улыбка сквозь обиду.",
  "rak-vodoley":
    "Близость по расписанию и близость по волне: разные языки любви. Интересно, когда Водолей приносит свежие идеи «как жить», а Рак — тепло без оценки «странно»; правило — сначала принять, потом обсуждать.",
  "ryby-skorpion":
    "Интуиция на максимуме: мало объясняют — много понимают. Опасность — тайны и подозрительность; сила — в совместном творчестве и в запрете на манипуляцию даже «ради блага».",
  "ryby-strelec":
    "Мечта и стрела: один рисует картину, другой натягивает тетиву. Вдохновляют друг друга на смысл; спорят о реализме vs вере — мирятся малыми шагами к большой цели и юмором после накала.",
  "ryby-telets":
    "Тишина, тело, красота мелочей: очень чувственный и домашний тандем. Риск — избегание конфликтов до переполнения; полезно договориться о «слове-тревоге», когда пора выговориться вслух.",
  "ryby-vesy":
    "Эстетика и эмпатия: красивые жесты, музыка, атмосфера. Легко раствориться в романтике; землю дают конкретные договорённости о деньгах и времени, чтобы воздушность не превратилась в хаос.",
  "ryby-vodoley":
    "Утопия и манифест: мечты обретут форму, если их записать. Один тянет к человечности, другой — к идее справедливости; сближает совместное доброе дело и запрет обесценивать «переживания» словом «логично».",
  "skorpion-strelec":
    "Глубина и ширина: один копает, другой обобщает. Страсть и споры о смысле жизни; выигрывают, когда соревнуются не в язвительности, а в честности и когда после спора есть объятия, а не молчание дней.",
  "skorpion-telets":
    "Властвование и упрямство: редко сдаются первыми. Союз крепкий, если есть общий материальный план и право на «я не готов говорить» без наказания; ревность — тема для правил, а не для тестов.",
  "skorpion-vesy":
    "Подтекст и гладкая поверхность: один читает скрытое, другой держит лицо. Опасность — недосказанность; сила — в эстетике и сексуальности пары и в умении называть ревность без театра.",
  "skorpion-vodoley":
    "Реформа души и реформа системы: нестандартный, интенсивный тандем. Интересно в психологии, науке, искусстве; границы личного пространства — священны, иначе свобода читается как предательство.",
  "strelec-telets":
    "Даль и поле: один смотрит на карту мира, другой — на урожай. Учат друг друга и риску, и терпению; спор о тратах лечится «подушкой безопасности» и одной большой совместной целью на квартал.",
  "strelec-vesy":
    "Идеи, люди, путешествия — вечер никогда не кончается. Легко быть «звёздами вечеринки»; глубина — в честности о моногамии и в разговоре без зрителей, когда шутки кончились.",
  "strelec-vodoley":
    "Манифест свободы в двух голосах: ценят автономию и смысл. Риск — эмоциональная отстранённость; близость — в совместных проектах для других и в редких, но тёплых признаниях без повода.",
  "telets-vesy":
    "Комфорт и красота: стол, дом, отношения к виду. Хорошо кормят друзей и себя; напряжение — когда гармония важнее правды; короткая прямота без упрёка спасает недели намёков.",
  "telets-vodoley":
    "Проверенные правила и исключения: один любит стабильность, другой — сбой шаблона. Интересно в дизайне, экологии, технике; мирятся зоной «тут можно эксперимент» и уважением к чужому «мне так спокойнее».",
  "vesy-vodoley":
    "Два архитектора смысла: справедливость, люди, будущее. Легко дружить умом; любовь — когда добавляют телесность и бытовую вовлечённость, а не только манифесты о свободе.",
};

function seoElementPairKey(ea, eb) {
  const [x, y] = [ea, eb].sort();
  return `${x}-${y}`;
}

/** Общий абзац по сочетанию стихий (покрывает все 66 уникальных пар знаков). */
function seoBaseParagraphByElements(ea, eb) {
  const c = seoElementPairKey(ea, eb);
  if (c === "Вода-Вода") {
    return (
      "Два водных знака: тонкая настройка на настроения и доверие. " +
      "Сила пары — в эмпатии и совместных ритуалах уюта; риск — перегруз переживаниями, " +
      "если не договариваться о границах и отдыхе."
    );
  }
  if (c === "Огонь-Огонь") {
    return (
      "Двойной огонь: драйв, вдохновение и смелые шаги. " +
      "Хорошо зажигают друг друга в проектах и приключениях; важно не соревноваться в громкости " +
      "и уметь приземляться к быту."
    );
  }
  if (c === "Земля-Земля") {
    return (
      "Земля и земля: надёжность, практичность, умение строить по шагам. " +
      "Союз держится на общих целях и честности; стоит следить, чтобы забота о деталях " +
      "не превращалась во взаимную критику."
    );
  }
  if (c === "Воздух-Воздух") {
    return (
      "Воздушный тандем: слова, идеи, социальные связи. " +
      "Легко находить общий язык; для глубины полезны совместные планы «на бумаге» " +
      "и время без гаджетов вдвоём."
    );
  }
  if (c === "Вода-Земля") {
    return (
      "Вода и земля: чувство встречает структуру. " +
      "Один партнёр даёт опору, другой — теплоту; гармония растёт, когда эмоции называются прямо, " +
      "а правила быта — мягко и по договорённости."
    );
  }
  if (c === "Вода-Огонь") {
    return (
      "Вода и огонь: страсть и чувствительность усиливают друг друга. " +
      "Нужны паузы для разговора без обвинений и ясные сигналы, когда каждому нужна поддержка, " +
      "а не «победа»."
    );
  }
  if (c === "Вода-Воздух") {
    return (
      "Вода и воздух: образы и смыслы оживляют чувства. " +
      "Интересно вместе мечтать и обсуждать людей; важно не уходить только в интеллект, " +
      "а намеренно возвращаться к телу и простым ритуалам близости."
    );
  }
  if (c === "Земля-Огонь") {
    return (
      "Земля и огонь: терпение и импульс. " +
      "Один стабилизирует, другой подталкивает к действию; конфликт возможен из-за темпа — " +
      "помогает общий календарь дел и уважение к «медленным» дням."
    );
  }
  if (c === "Земля-Воздух") {
    return (
      "Земля и воздух: идеи получают опору в реальности. " +
      "Пара сильна в планировании и дискуссиях; выигрывает, когда воздушный партнёр не обесценивает быт, " +
      "а земной — не гасит любопытство."
    );
  }
  if (c === "Воздух-Огонь") {
    return (
      "Воздух и огонь: яркие разговоры и смелые поступки. " +
      "Легко заводить новое; стоит договориться, кто ведёт документы и финансы, " +
      "чтобы азарт не превращался в хаос."
    );
  }
  return (
    "Разные стихии дополняют сильные стороны. " +
    "Успех — в переводе различий на язык уважения и совместных правил, а не «кто прав»."
  );
}

/** Текстовое описание для любой пары знаков (12×11/2 комбинаций). */
function buildSeoPairArticle(sign1Ru, sign2Ru, slug1, slug2) {
  const e1 = ZODIAC_ELEMENT_BY_SLUG[slug1];
  const e2 = ZODIAC_ELEMENT_BY_SLUG[slug2];
  const t1 = SIGN_TRAIT_BY_SLUG[slug1];
  const t2 = SIGN_TRAIT_BY_SLUG[slug2];
  if (!e1 || !e2 || !t1 || !t2) {
    return "";
  }
  const end =
    " Итоговый балл калькулятора — ориентир: смотрите блоки аспектов и нумерологии выше для деталей.";
  const pairKey = seoSlugPairKey(slug1, slug2);
  const hand = pairKey ? SEO_PAIR_HANDCRAFTED[pairKey] : "";
  if (hand) {
    return `${hand}${end}`;
  }
  const base = seoBaseParagraphByElements(e1, e2);
  const mid =
    sign1Ru === sign2Ru
      ? ` У обоих заметны ${t1}; ищите баланс между опорой на привычное и мягкой сменой ролей.`
      : ` У ${signRuGenitive(sign1Ru)} заметны ${t1}, у ${signRuGenitive(sign2Ru)} — ${t2}; ищите баланс без попытки «переучить» друг друга.`;
  return `${base}${mid}${end}`;
}

function signRuToSlug(signName) {
  const s = (signName || "").trim();
  return ZODIAC_SIGN_SLUG[s] || null;
}

function buildCompatHash(slug1, slug2) {
  if (!slug1 || !slug2) return "";
  return `#sovmestimost/${slug1}-i-${slug2}`;
}

function parseCompatHash(hash) {
  if (!hash || typeof hash !== "string" || !hash.startsWith("#sovmestimost/")) return null;
  const path = hash.slice("#sovmestimost/".length).split("?")[0];
  const sep = "-i-";
  const j = path.indexOf(sep);
  if (j === -1) return null;
  const slug1 = path.slice(0, j);
  const slug2 = path.slice(j + sep.length);
  if (!slug1 || !slug2) return null;
  if (!VALID_SIGN_SLUG_SET.has(slug1) || !VALID_SIGN_SLUG_SET.has(slug2)) return null;
  return { slug1, slug2 };
}

function applyHashPairToForm(slug1, slug2) {
  const b1 = document.getElementById("birth1");
  const b2 = document.getElementById("birth2");
  if (!b1 || !b2) return;
  const d1 = SLUG_SAMPLE_BIRTH[slug1];
  const d2 = SLUG_SAMPLE_BIRTH[slug2];
  if (!d1 || !d2) return;
  b1.value = d1;
  b2.value = d2;
}

/** Подставить даты под пару из хэша и отправить форму (как клик «Рассчитать»). */
function runCompatFromHashRoute() {
  if (!compatibilityForm) return;
  const parsed = parseCompatHash(window.location.hash);
  if (!parsed) return;
  applyHashPairToForm(parsed.slug1, parsed.slug2);
  if (typeof compatibilityForm.requestSubmit === "function") {
    compatibilityForm.requestSubmit();
  } else {
    compatibilityForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
}

function buildSharePathQueryHash() {
  const params = new URLSearchParams(buildFormQueryString());
  const fromUrl = new URLSearchParams(window.location.search);
  for (const [key, value] of fromUrl.entries()) {
    if (!COMPAT_FORM_QUERY_KEY_SET.has(key)) {
      params.set(key, value);
    }
  }
  const q = params.toString();
  const pathQuery = q ? `${window.location.pathname}?${q}` : window.location.pathname;
  return pathQuery + (compatibilityUrlHash || "");
}

function updateSEO(sign1, sign2, typeLocative) {
  const titleEl = document.getElementById("dynamic-title");
  const descEl = document.getElementById("dynamic-desc");
  if (!titleEl || !descEl) return;
  const t = `${sign1} и ${sign2}: совместимость в ${typeLocative} | MagicLove`;
  const d = `Гороскоп совместимости: ${sign1} + ${sign2}. Анализ характеров, советы астролога и прогноз отношений. Рассчитайте бесплатно онлайн на MagicLove.`;
  titleEl.textContent = t;
  descEl.setAttribute("content", d);
}

function buildSchemaAnswerText(sign1, sign2, rating) {
  if (rating >= 75) {
    return `По расчёту калькулятора MagicLove совместимость ${sign1} и ${sign2} оценивается примерно в ${rating} из 100 баллов: сильный потенциал пары при готовности обоих поддерживать диалог и уважение.`;
  }
  if (rating >= 55) {
    return `Совместимость ${sign1} и ${sign2} в расчёте — около ${rating} из 100: есть гармоничные зоны и темы для проработки; результат носит ознакомительный характер.`;
  }
  return `Расчёт показывает порядка ${rating} из 100 для пары ${sign1} и ${sign2}; это ориентир для размышлений, а не готовый прогноз судьбы.`;
}

function addSchemaMarkup(sign1, sign2, rating) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: `Какая совместимость у пары ${sign1} и ${sign2}?`,
        acceptedAnswer: {
          "@type": "Answer",
          text: buildSchemaAnswerText(sign1, sign2, rating),
        },
      },
    ],
  };
  const oldScript = document.getElementById("json-ld-schema");
  if (oldScript) oldScript.remove();
  const script = document.createElement("script");
  script.type = "application/ld+json";
  script.id = "json-ld-schema";
  script.text = JSON.stringify(schema);
  document.head.appendChild(script);
}

function setSeoToggleUi(expanded) {
  const btn = document.getElementById("toggle-seo-text");
  if (!btn) return;
  btn.setAttribute("aria-expanded", expanded ? "true" : "false");
  const lbl = btn.querySelector(".seo-text-toggle__label");
  const icon = btn.querySelector(".seo-text-toggle__icon");
  if (lbl) lbl.textContent = expanded ? "Свернуть" : "Читать подробнее";
  if (icon) icon.textContent = expanded ? "▲" : "▼";
}

function showSEOText(sign1, sign2, bodyText) {
  const block = document.getElementById("seo-text-block");
  const h3 = document.getElementById("seo-h3-signs");
  const content = document.getElementById("seo-text-content");
  const coll = document.getElementById("seo-text-collapsible");
  if (!block || !h3 || !content) return;
  h3.textContent = `${sign1} и ${sign2}`;
  content.textContent = bodyText;
  block.classList.remove("hidden");
  if (coll) coll.classList.remove("seo-text-collapsible--expanded");
  setSeoToggleUi(false);
}

function resetSeoToDefaults() {
  compatibilityUrlHash = "";
  const titleEl = document.getElementById("dynamic-title");
  const descEl = document.getElementById("dynamic-desc");
  if (titleEl) titleEl.textContent = DEFAULT_PAGE_TITLE;
  if (descEl) descEl.setAttribute("content", DEFAULT_PAGE_DESC);
  const oldScript = document.getElementById("json-ld-schema");
  if (oldScript) oldScript.remove();
  const block = document.getElementById("seo-text-block");
  if (block) {
    block.classList.add("hidden");
    const coll = document.getElementById("seo-text-collapsible");
    if (coll) coll.classList.remove("seo-text-collapsible--expanded");
    setSeoToggleUi(false);
  }
}

function applyResultSeo(result) {
  const sign1 = (result.western?.sign1 || "").trim();
  const sign2 = (result.western?.sign2 || "").trim();
  const slug1 = signRuToSlug(sign1);
  const slug2 = signRuToSlug(sign2);
  const relKey = document.getElementById("relationshipType")?.value || "romance";
  const typeLoc = RELATIONSHIP_LOCATIVE[relKey] || RELATIONSHIP_LOCATIVE.romance;

  if (sign1 && sign2 && sign1 !== "—" && sign2 !== "—") {
    updateSEO(sign1, sign2, typeLoc);
    addSchemaMarkup(sign1, sign2, Number(result.total) || 0);
    const fallback =
      `Стихии ${result.western.element1} и ${result.western.element2}. ` +
      `Балл совместимости в расчёте — ${result.total} из 100. Подробнее по аспектам, нумерологии и китайскому циклу — в блоках выше; ` +
      `это развлекательный ориентир, а не медицинское или юридическое заключение.`;
    const article = slug1 && slug2 ? buildSeoPairArticle(sign1, sign2, slug1, slug2) : "";
    showSEOText(sign1, sign2, article || fallback);
  } else {
    resetSeoToDefaults();
    const block = document.getElementById("seo-text-block");
    if (block) block.classList.add("hidden");
  }

  compatibilityUrlHash = slug1 && slug2 ? buildCompatHash(slug1, slug2) : "";
}

function expandMinimalCompatibilityResult(r) {
  if (r.advanced?.aspects?.mercury) {
    return r;
  }
  const elDyn =
    r.western?.element1 && r.western?.element2
      ? `Стихии ${r.western.element1} и ${r.western.element2}: смотрите полный расчёт на сервере с Swiss Ephemeris.`
      : "";
  const place = {
    moon1: "—",
    moon2: "—",
    moonAspect: "—",
    ...r.bonus,
  };
  return {
    ...r,
    western: {
      sign1: r.western?.sign1 || "—",
      sign2: r.western?.sign2 || "—",
      element1: r.western?.element1 || "",
      element2: r.western?.element2 || "",
      venusAspect: r.western?.venusAspect || "н/д",
      marsAspect: r.western?.marsAspect || "н/д",
      mercuryAspect: r.western?.mercuryAspect || "н/д",
      jupiterAspect: r.western?.jupiterAspect || "н/д",
      saturnAspect: r.western?.saturnAspect || "н/д",
      elementDynamics: r.western?.elementDynamics || elDyn,
    },
    bonus: place,
    birthMeta: r.birthMeta || {
      city1: "",
      city2: "",
      timezone1: "UTC",
      timezone2: "UTC",
    },
    numerology: {
      lifePath1: r.numerology?.lifePath1 ?? 0,
      lifePath2: r.numerology?.lifePath2 ?? 0,
      destiny1: r.numerology?.destiny1,
      destiny2: r.numerology?.destiny2,
      personalYear1: r.numerology?.personalYear1 ?? "—",
      personalYear2: r.numerology?.personalYear2 ?? "—",
    },
    advanced: {
      chineseDynamics:
        r.advanced?.chineseDynamics ||
        "Полная китайская динамика доступна при расчёте на основном сервере.",
      pairFlags: r.advanced?.pairFlags || {
        green: ["Упрощённый режим CDN: укажите backend с полным API для деталей."],
        red: [],
      },
      areaScores: r.advanced?.areaScores || {
        быт: 50,
        секс: 50,
        деньги: 50,
        коммуникация: 50,
        цели: 50,
      },
      bestDays: r.advanced?.bestDays || [],
      energyTrend: r.advanced?.energyTrend || [],
      aspects: {
        venus: { name: "н/д", orb: 0 },
        mars: { name: "н/д", orb: 0 },
        moon: { name: "н/д", orb: 0 },
        mercury: { name: "н/д", orb: 0 },
        jupiter: { name: "н/д", orb: 0 },
        saturn: { name: "н/д", orb: 0 },
        ...r.advanced?.aspects,
      },
      planetPositions: r.advanced?.planetPositions || {
        first: {},
        second: {},
      },
      compatibilityVector: r.advanced?.compatibilityVector || {
        emotional: 50,
        communication: 50,
        passion: 50,
        stability: 50,
      },
      timeline: r.advanced?.timeline || {
        m3: "",
        m6: "",
        m12: "",
      },
    },
    insights: {
      strengths: r.insights?.strengths || [],
      growth: r.insights?.growth || [],
      weeklyAdvice: r.insights?.weeklyAdvice || "",
      conflictTip: r.insights?.conflictTip || "",
      forecastTip: r.insights?.forecastTip || "",
      funTip: r.insights?.funTip || "",
    },
  };
}

/** Поля формы в query string; остальные параметры URL сохраняются при «Поделиться» и replaceState. */
const COMPAT_FORM_QUERY_KEYS = [
  "name1",
  "name2",
  "birth1",
  "birth2",
  "birthTime1",
  "birthTime2",
  "city1",
  "city2",
  "timezone1",
  "timezone2",
  "relationshipType",
];

const COMPAT_FORM_QUERY_KEY_SET = new Set(COMPAT_FORM_QUERY_KEYS);

function buildFormQueryString() {
  const params = new URLSearchParams();
  COMPAT_FORM_QUERY_KEYS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const v = el.value != null ? String(el.value).trim() : "";
    if (v) params.set(id, v);
  });
  return params.toString();
}

function applyQueryToForm(params) {
  COMPAT_FORM_QUERY_KEYS.forEach((id) => {
    const el = document.getElementById(id);
    if (!el || !params.has(id)) return;
    el.value = params.get(id);
  });
}

function getShareUrlWithParams() {
  return `${window.location.origin}${buildSharePathQueryHash()}`;
}

let geoTimer1;
let geoTimer2;

function setupGeoSuggest(cityInputId, listId, tzInputId) {
  const input = document.getElementById(cityInputId);
  const list = document.getElementById(listId);
  const tzInput = document.getElementById(tzInputId);
  if (!input || !list || !tzInput) return;

  const hide = () => {
    list.classList.add("hidden");
    list.innerHTML = "";
  };

  input.addEventListener("blur", () => {
    setTimeout(hide, 200);
  });

  input.addEventListener("input", () => {
    const timerRef = cityInputId === "city1" ? geoTimer1 : geoTimer2;
    clearTimeout(timerRef);
    const q = input.value.trim();
    if (q.length < 2) {
      hide();
      return;
    }
    const run = async () => {
      try {
        const url = `${GEO_SEARCH_URL}?name=${encodeURIComponent(q)}&count=6&language=ru`;
        const res = await fetch(url);
        const data = await res.json();
        const results = data.results || [];
        list.innerHTML = "";
        if (!results.length) {
          hide();
          return;
        }
        results.forEach((place) => {
          const li = document.createElement("li");
          const label = place.name + (place.admin1 ? `, ${place.admin1}` : "") + ` — ${place.country}`;
          li.textContent = label;
          li.setAttribute("role", "option");
          li.addEventListener("mousedown", (e) => {
            e.preventDefault();
            input.value = place.name;
            if (place.timezone) {
              tzInput.value = place.timezone;
            }
            hide();
          });
          list.appendChild(li);
        });
        list.classList.remove("hidden");
      } catch {
        hide();
      }
    };
    if (cityInputId === "city1") {
      geoTimer1 = setTimeout(run, 280);
    } else {
      geoTimer2 = setTimeout(run, 280);
    }
  });
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("compat-theme", theme);
  if (window.tsParticlesInstance) {
    const colors = theme === "light" 
      ? ["#7c3aed", "#db2777", "#059669"]
      : ["#a78bfa", "#f472b6", "#34d399"];
    window.tsParticlesInstance.options.particles.color.value = colors;
    window.tsParticlesInstance.refresh();
  }
}

function initTheme() {
  const saved = localStorage.getItem("compat-theme");
  const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
  setTheme(saved || (prefersLight ? "light" : "dark"));
}

function listItems(target, items) {
  target.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function drawChart(score) {
  if (chart) chart.destroy();
  const ctx = document.getElementById("scoreChart");
  chart = new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [score, 100 - score],
          backgroundColor: ["#8a6bff", "rgba(255,255,255,0.15)"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      cutout: "72%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
    },
  });
}

function drawEnergyTrend(trend, bestDays = []) {
  if (!energyTrendChart || !Array.isArray(trend)) return;
  if (trendChart) trendChart.destroy();

  const labels = trend.map((item) => item.date.slice(5));
  const values = trend.map((item) => item.score);
  const bestDayDates = new Set(bestDays.map((day) => day.date));
  const markerValues = trend.map((item) =>
    bestDayDates.has(item.date) ? item.score : null
  );

  trendChart = new Chart(energyTrendChart, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Энергия пары",
          data: values,
          borderColor: "#8a6bff",
          backgroundColor: "rgba(138,107,255,0.2)",
          tension: 0.35,
          fill: true,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: "Топ-5 дней",
          data: markerValues,
          showLine: false,
          pointRadius: 5,
          pointHoverRadius: 6,
          pointBackgroundColor: "#ff5db1",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
      scales: {
        x: { ticks: { maxTicksLimit: 6, color: "#8b92be" }, grid: { display: false } },
        y: { ticks: { maxTicksLimit: 4, color: "#8b92be" }, grid: { color: "rgba(255,255,255,0.08)" } },
      },
    },
  });
}

async function showLoading() {
  resetSeoToDefaults();
  loaderSection.classList.remove("hidden");
  resultSection.classList.add("hidden");
  progressBar.style.width = "0%";
  const steps = 36;
  for (let i = 1; i <= steps; i += 1) {
    progressBar.style.width = `${Math.round((i / steps) * 100)}%`;
    await new Promise((resolve) => setTimeout(resolve, 170));
  }
}

function renderResult(result, person1, person2) {
  result = expandMinimalCompatibilityResult(result);
  const title1 = person1 || "Вы";
  const title2 = person2 || "Партнер";
  resultTitle.textContent = `💕 Совместимость: ${result.total}/100`;
  resultSubtitle.textContent = `${title1} + ${title2} | ${result.relationProfile.label}`;

  westernText.textContent = `${result.western.sign1} + ${result.western.sign2}: стихии ${result.western.element1} и ${result.western.element2}. Венера: ${result.western.venusAspect}, Марс: ${result.western.marsAspect}. Меркурий: ${result.western.mercuryAspect}, Юпитер: ${result.western.jupiterAspect}, Сатурн: ${result.western.saturnAspect}.`;
  chineseText.textContent = `${result.chinese.first.animal} (${result.chinese.first.element}) + ${result.chinese.second.animal} (${result.chinese.second.element}): ${result.advanced.chineseDynamics}`;
  numerologyText.textContent = `ЧЖП: ${result.numerology.lifePath1} + ${result.numerology.lifePath2}. ${
    result.numerology.destiny1 && result.numerology.destiny2
      ? `Число судьбы по именам: ${result.numerology.destiny1} и ${result.numerology.destiny2}. `
      : ""
  }Личный год: ${result.numerology.personalYear1} / ${result.numerology.personalYear2}.`;
  const cityLine =
    result.birthMeta?.city1 || result.birthMeta?.city2
      ? ` Гео: ${result.birthMeta?.city1 || "не указано"} / ${result.birthMeta?.city2 || "не указано"}.`
      : "";
  bonusText.textContent = `Луна ${title1}: ${result.bonus.moon1}, Луна ${title2}: ${result.bonus.moon2}. Между ними: ${result.bonus.moonAspect}. Часовые пояса: ${result.birthMeta?.timezone1 || "UTC"} и ${result.birthMeta?.timezone2 || "UTC"}.${cityLine}`;
  aspectsText.textContent = `Венера: ${result.advanced.aspects.venus.name} (${result.advanced.aspects.venus.orb}°), Марс: ${result.advanced.aspects.mars.name} (${result.advanced.aspects.mars.orb}°), Луна: ${result.advanced.aspects.moon.name} (${result.advanced.aspects.moon.orb}°). Меркурий: ${result.advanced.aspects.mercury.name} (${result.advanced.aspects.mercury.orb}°), Юпитер: ${result.advanced.aspects.jupiter.name} (${result.advanced.aspects.jupiter.orb}°), Сатурн: ${result.advanced.aspects.saturn.name} (${result.advanced.aspects.saturn.orb}°).`;
  vectorText.textContent = `Эмоции ${result.advanced.compatibilityVector.emotional}/100, Коммуникация ${result.advanced.compatibilityVector.communication}/100, Страсть ${result.advanced.compatibilityVector.passion}/100, Стабильность ${result.advanced.compatibilityVector.stability}/100.`;
  timelineText.textContent = `${result.advanced.timeline.m3} ${result.advanced.timeline.m6} ${result.advanced.timeline.m12}`;
  dynamicsText.textContent = `${result.western.elementDynamics} Позиции Солнца: ${result.advanced.planetPositions.first.sun}° / ${result.advanced.planetPositions.second.sun}°.`;
  listItems(greenFlagsList, result.advanced.pairFlags.green);
  listItems(redFlagsList, result.advanced.pairFlags.red);
  areasText.textContent = `Быт ${result.advanced.areaScores["быт"]}/100, Секс ${result.advanced.areaScores["секс"]}/100, Деньги ${result.advanced.areaScores["деньги"]}/100, Коммуникация ${result.advanced.areaScores["коммуникация"]}/100, Цели ${result.advanced.areaScores["цели"]}/100.`;
  listItems(
    bestDaysList,
    result.advanced.bestDays.map(
      (day) => `${day.date}: ${day.phase}. ${day.reason}`
    )
  );
  drawEnergyTrend(result.advanced.energyTrend, result.advanced.bestDays);

  listItems(strengthsList, result.insights.strengths);
  listItems(growthList, result.insights.growth);
  weeklyAdvice.textContent = result.insights.weeklyAdvice;
  conflictTip.textContent = result.insights.conflictTip;
  forecastTip.textContent = result.insights.forecastTip;
  funTip.textContent = result.insights.funTip;

  drawChart(result.total);
  applyResultSeo(result);
  loaderSection.classList.add("hidden");
  resultSection.classList.remove("hidden");
}

async function requestCompatibility(payload) {
  const response = await fetch("/api/compatibility", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Ошибка расчета");
  }
  return data;
}

compatibilityForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    name1: document.getElementById("name1").value.trim(),
    name2: document.getElementById("name2").value.trim(),
    birth1: document.getElementById("birth1").value,
    birth2: document.getElementById("birth2").value,
    birthTime1: document.getElementById("birthTime1").value,
    birthTime2: document.getElementById("birthTime2").value,
    city1: document.getElementById("city1").value.trim(),
    city2: document.getElementById("city2").value.trim(),
    timezone1: document.getElementById("timezone1").value.trim() || "UTC",
    timezone2: document.getElementById("timezone2").value.trim() || "UTC",
    relationshipType: document.getElementById("relationshipType").value,
  };
  if (!payload.birth1 || !payload.birth2) return;

  try {
    await showLoading();
    latestResult = await requestCompatibility(payload);
    latestResult.shareNames = [payload.name1, payload.name2];
    renderResult(latestResult, payload.name1, payload.name2);
    window.history.replaceState({}, "", buildSharePathQueryHash());
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    loaderSection.classList.add("hidden");
    alert(error.message || "Не удалось рассчитать совместимость.");
  }
});

shareBtn.addEventListener("click", async () => {
  if (!latestResult) return;
  const shareUrl = getShareUrlWithParams();
  const shareText = `Наша совместимость: ${latestResult.total}/100. Расчёт калькулятора ✨`;
  try {
    if (navigator.share) {
      await navigator.share({
        title: "Калькулятор совместимости",
        text: shareText,
        url: shareUrl,
      });
      return;
    }
    await navigator.clipboard.writeText(`${shareText}\n${shareUrl}`);
    alert("Текст и ссылка скопированы в буфер обмена.");
  } catch (_error) {
    alert("Не удалось поделиться. Используйте «Копировать ссылку».");
  }
});

if (copyLinkBtn) {
  copyLinkBtn.addEventListener("click", async () => {
    const url = getShareUrlWithParams();
    try {
      await navigator.clipboard.writeText(url);
      alert("Ссылка скопирована — при открытии подставятся даты расчёта.");
    } catch {
      prompt("Скопируйте ссылку:", url);
    }
  });
}

if (printPdfBtn) {
  printPdfBtn.addEventListener("click", () => {
    if (!latestResult) return;
    window.print();
  });
}

downloadPngBtn.addEventListener("click", async () => {
  if (!latestResult) return;
  const node = document.getElementById("resultSection");
  const canvas = await html2canvas(node, {
    backgroundColor: null,
    useCORS: true,
    scale: 2,
  });
  const link = document.createElement("a");
  link.download = `compatibility-${latestResult.total}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
});

expertBtn.addEventListener("click", () => {
  document.getElementById("crmName").focus();
  crmForm.scrollIntoView({ behavior: "smooth", block: "center" });
});

crmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  crmStatus.className = "status-text";
  crmStatus.textContent = "Отправляем заявку...";
  const payload = {
    name: document.getElementById("crmName").value.trim(),
    contact: document.getElementById("crmContact").value.trim(),
    message: document.getElementById("crmMessage").value.trim(),
    context: latestResult
      ? {
          score: latestResult.total,
          relationType: latestResult.relationProfile.label,
          timezone1: latestResult.birthMeta?.timezone1,
          timezone2: latestResult.birthMeta?.timezone2,
          city1: latestResult.birthMeta?.city1,
          city2: latestResult.birthMeta?.city2,
        }
      : {},
  };
  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Не удалось отправить заявку");
    }
    crmStatus.className = "status-text success";
    crmStatus.textContent = "Заявка отправлена. Мы свяжемся с вами в ближайшее время.";
    crmForm.reset();
  } catch (error) {
    crmStatus.className = "status-text error";
    crmStatus.textContent = error.message || "Ошибка отправки.";
  }
});

themeToggle.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  setTheme(current === "dark" ? "light" : "dark");
});

initTheme();

setupGeoSuggest("city1", "geoSuggest1", "timezone1");
setupGeoSuggest("city2", "geoSuggest2", "timezone2");

const toggleSeoBtn = document.getElementById("toggle-seo-text");
if (toggleSeoBtn) {
  toggleSeoBtn.addEventListener("click", () => {
    const coll = document.getElementById("seo-text-collapsible");
    if (!coll) return;
    const expanded = coll.classList.toggle("seo-text-collapsible--expanded");
    setSeoToggleUi(expanded);
  });
}

window.addEventListener("hashchange", () => {
  if (!window.location.hash.startsWith("#sovmestimost/")) return;
  if (parseCompatHash(window.location.hash)) {
    runCompatFromHashRoute();
    return;
  }
  const rs = document.getElementById("resultSection");
  if (rs && !rs.classList.contains("hidden")) {
    rs.scrollIntoView({ behavior: "smooth", block: "start" });
  }
});

(() => {
  const params = new URLSearchParams(window.location.search);
  // Параметры _ym* добавляет Метрика (проверка счётчика, отладка). Автоотправка формы даёт replaceState и лишнюю нагрузку до загрузки tag.js.
  if ([...params.keys()].some((k) => k.startsWith("_ym"))) return;
  if (params.has("birth1") && params.has("birth2")) {
    applyQueryToForm(params);
    if (typeof compatibilityForm.requestSubmit === "function") {
      compatibilityForm.requestSubmit();
    } else {
      compatibilityForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
    }
    return;
  }
  if (window.location.hash.startsWith("#sovmestimost/")) {
    runCompatFromHashRoute();
  }
})();

window.tsParticlesInstance = null;

tsParticles.load("particles", {
  options: {
    background: { color: "transparent" },
    fpsLimit: 60,
    particles: {
      number: { value: 34 },
      color: { value: ["#a78bfa", "#f472b6", "#34d399"] },
      shape: { type: "circle" },
      opacity: { value: { min: 0.15, max: 0.45 } },
      size: { value: { min: 1, max: 3 } },
      move: { enable: true, speed: 1.2, outModes: { default: "out" } },
      links: {
        enable: true,
        distance: 140,
        color: { value: "inherit" },
        opacity: { value: 0.2 },
      },
    },
  },
}).then((container) => {
  window.tsParticlesInstance = container;
});

const decorStars = document.getElementById("decorStars");
if (decorStars) {
  for (let i = 0; i < 50; i++) {
    const star = document.createElement("div");
    star.className = "star";
    const size = Math.random() * 2 + 1;
    star.style.width = size + "px";
    star.style.height = size + "px";
    star.style.left = Math.random() * 100 + "%";
    star.style.top = Math.random() * 100 + "%";
    star.style.animationDelay = Math.random() * 3 + "s";
    star.style.animationDuration = (Math.random() * 2 + 2) + "s";
    decorStars.appendChild(star);
  }
}

const chatToggle = document.getElementById("chatToggle");
const chatPanel = document.getElementById("chatPanel");
const chatClose = document.getElementById("chatClose");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatMessages = document.getElementById("chatMessages");

let chatSessionId = localStorage.getItem("chat-session") || crypto.randomUUID();
localStorage.setItem("chat-session", chatSessionId);

let chatInitialized = localStorage.getItem("chat-initialized") === "true";

function initChat() {
  if (!chatInitialized) {
    addMessage(
      "Привет! Я коуч по отношениям — отвечу бесплатно, без регистрации. Переписку не показываем другим. Расскажите, что хотите разобрать.",
      "assistant",
    );
    chatInitialized = true;
    localStorage.setItem("chat-initialized", "true");
  }
}

if (chatToggle && chatPanel) {
  chatToggle.onclick = function() {
    chatPanel.classList.remove("hidden");
    chatToggle.style.display = "none";
    chatInput.focus();
    initChat();
  };
}

if (chatClose && chatPanel && chatToggle) {
  chatClose.onclick = function() {
    chatPanel.classList.add("hidden");
    chatToggle.style.display = "";
  };
}

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `chat-message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
  const div = document.createElement("div");
  div.className = "chat-message typing typing-indicator";
  div.id = "typingIndicator";
  div.setAttribute("aria-live", "polite");
  div.innerHTML =
    '<span class="typing-label">Эксперт отвечает</span><span class="typing-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function hideTyping() {
  const typing = document.getElementById("typingIndicator");
  typing?.remove();
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  const sendBtn = chatForm.querySelector(".chat-send");
  if (sendBtn) sendBtn.disabled = true;
  chatInput.disabled = true;

  addMessage(message, "user");
  chatInput.value = "";

  const typing = showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: chatSessionId }),
    });
    const data = await response.json();
    typing.remove();
    if (!response.ok) {
      addMessage(data.error || "Не удалось получить ответ", "assistant");
      return;
    }
    addMessage(data.reply, "assistant");
  } catch (error) {
    typing.remove();
    addMessage("Ошибка соединения. Попробуйте ещё раз.", "assistant");
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
});
