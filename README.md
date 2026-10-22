# Факторизація числа методом пробних дільників на PARCS-Python (Google Cloud)

Лабораторна робота 1 з курсу «Хмарні обчислення»: послідовний і паралельний алгоритм
факторизації, кластер PARCS-Python у Google Cloud, тестування для різної кількості воркерів.

## Структура репозиторію

```
factorization.py          # послідовний + паралельний алгоритм (рішення для PARCS-Python)
local_run.py              # локальна перевірка без кластера (воркери - процеси)
inputs/                   # вхідні дані: n у першому рядку, режим (both|seq|par) у другому
  01_check.txt              600851475143 = 71 * 839 * 1471 * 6857 (перевірка коректності)
  02_semiprime_1e12.txt     1000003 * 1001003
  03_semiprime_1e14.txt     10000019 * 10001053
  04_semiprime_1e16.txt     100000007 * 100001029
  05_semiprime_1e17.txt     300000007 * 300001033
  06_semiprime_1e18.txt     1000000007 * 1000001011
  07_prime_1e17.txt         100000000000000003 (просте число)
deploy/
  create_cluster.sh       # створює майстра і воркерів у Compute Engine
  startup-master.sh       # запускає контейнер PARCS у режимі master
  startup-worker.sh       # запускає контейнер PARCS у режимі worker
  delete_cluster.sh       # видаляє все створене
bench.py                  # автоматичний прогін тестів через REST API PARCS -> results.csv
```

## Формат вхідних і вихідних даних

Вхідний файл:

```
10000103600007203
both
```

Перший рядок — число `n ≥ 2`. Другий (необов'язковий) — режим: `both` (послідовний і паралельний,
за замовчуванням), `seq` (лише послідовний), `par` (лише паралельний).

Вихідний файл (`output.txt`, вкладка **Jobs → Output**) містить розклад, час кожного алгоритму,
збіг результатів, прискорення `S = T_seq / T_par` і ефективність `E = S / k`.

## Локальна перевірка (без хмари)

Потрібен лише Python 3; воркери імітуються процесами (Pyro4 не потрібен):

```bash
python3 local_run.py inputs/01_check.txt              # 2 процеси
python3 local_run.py inputs/04_semiprime_1e16.txt 4   # 4 процеси
```

---

## Розгортання в Google Cloud

> **Чому не `gcloud compute instances create-with-container`, як у старих інструкціях.**
> Агент запуску контейнерів (konlet), на якому працювала ця команда, Google вивів з ужитку:
> він застарів 21.07.2025 і вимкнений 31.07.2026. Тому тут використано рекомендовану заміну —
> образ **Container-Optimized OS** (Docker вже встановлено) + **startup-скрипт**, який робить
> `docker run`. Сам Docker-образ той самий: `hummer12007/parcs-node`.

Схема кластера: 1 ВМ-майстер (веб-інтерфейс і планувальник на порту 8080) + 6 ВМ-воркерів.
Тип ВМ — `n1-standard-1` (1 vCPU): Python-процес використовує одне ядро, тому один воркер = одне ядро,
і порівняння чесне. Разом 7 vCPU — це вкладається в ліміт free trial (8 vCPU одночасно).

### Крок 1. Акаунт і проєкт

1. Активуйте безкоштовний пробний період: <https://cloud.google.com/free>
   (або освітні кредити, якщо видав викладач).
2. Відкрийте <https://console.cloud.google.com>, створіть проєкт (наприклад, `parcs-lab1`)
   і переконайтеся, що до нього прив'язано платіжний акаунт (Billing) з trial-кредитом.
3. Запам'ятайте **Project ID** (він може відрізнятися від назви).

### Крок 2. Cloud Shell і код

1. У консолі натисніть кнопку **Activate Cloud Shell** (`>_` вгорі праворуч).
   У Cloud Shell вже є `gcloud`, `git`, `python3` і `requests`.
2. Виберіть проєкт і завантажте код:

```bash
gcloud config set project <PROJECT_ID>
git clone https://github.com/<ваш-логін>/parcs-factorization.git
cd parcs-factorization
chmod +x deploy/*.sh
```

(Якщо репозиторій ще не створено — у меню Cloud Shell **⋮ → Upload** завантажте архів з файлами.)

### Крок 3. Ваша IP-адреса

Веб-інтерфейс PARCS не має авторизації, тому порт 8080 відкриваємо лише для вашої IP.
Відкрийте у **своєму браузері** <https://api.ipify.org> — це і є `MY_IP`.
(IP Cloud Shell скрипт додає сам — вона потрібна для `bench.py`.)

### Крок 4. Створення кластера

```bash
MY_IP=93.170.12.34 ./deploy/create_cluster.sh
```

Скрипт:
* вмикає Compute Engine API;
* створює правила брандмауера: `parcs-internal` (вузли кластера між собою — HTTP і порти Pyro4)
  та `parcs-web` (порт 8080 майстра лише для `MY_IP` і Cloud Shell);
* створює ВМ `parcs-master` з `startup-master.sh`;
* створює `parcs-worker-1 … parcs-worker-6`, передаючи їм внутрішню IP майстра в метаданих
  (`parcs-master-ip`), яку читає `startup-worker.sh`.

Параметри можна змінити змінними середовища:

```bash
ZONE=europe-west1-b MACHINE=n1-standard-1 WORKERS=4 MY_IP=93.170.12.34 ./deploy/create_cluster.sh
```

Наприкінці скрипт виведе адресу `http://<EXTERNAL_IP>:8080`.

### Крок 5. Перевірка кластера

Через 1–3 хвилини (ВМ завантажується і качає Docker-образ) відкрийте `http://<EXTERNAL_IP>:8080`.
На вкладці **Workers** мають бути 6 воркерів.

Якщо воркерів немає:

```bash
gcloud compute ssh parcs-master  --command "sudo docker ps; sudo docker logs --tail 30 parcs"
gcloud compute ssh parcs-worker-1 --command "sudo docker logs --tail 30 parcs"
gcloud compute ssh parcs-worker-1 --command "sudo journalctl -u google-startup-scripts --no-pager | tail -30"
```

Типові причини: власний фаєрвол COS блокує вхідні (вирішено рядком `iptables -w -I INPUT -j ACCEPT` у startup-скриптах); образ ще завантажується (зачекайте); помилка у квоті vCPU
(зменшіть `WORKERS` або змініть зону); не та `MY_IP` (перевірте ще раз і
перестворіть правило — простіше перезапустити `create_cluster.sh` після `delete_cluster.sh`).

### Крок 6. Запуск задачі вручну (через веб-інтерфейс)

1. **Add Job**: Job Name — довільна назва; Solution File — `factorization.py`;
   Input File — наприклад `inputs/01_check.txt` (його треба мати на своєму ПК:
   скачайте з GitHub або з Cloud Shell через **⋮ → Download**).
2. **Jobs**: дочекайтеся завершення, натисніть **Output**.
3. Кількість воркерів для запуску змінюється на вкладці **Workers** кнопками
   **Disable / Enable** — PARCS використовує лише ввімкнені.

### Крок 7. Автоматичне тестування (рекомендовано для звіту)

`bench.py` сам вмикає потрібну кількість воркерів, запускає задачі й збирає час:

```bash
export MASTER=http://<EXTERNAL_IP>:8080
python3 bench.py inputs/01_check.txt inputs/04_semiprime_1e16.txt \
    inputs/05_semiprime_1e17.txt inputs/07_prime_1e17.txt inputs/06_semiprime_1e18.txt \
    --workers 1 2 3 4 5 6
```

Для кожного файлу один раз виконується послідовний алгоритм (на майстрі),
потім паралельний для k = 1…6. Таблиця друкується в консолі і зберігається в `results.csv`
(скачати: **⋮ → Download**). Повний прогін займає приблизно 10–20 хвилин.
Ці числа вносяться в таблицю 3 звіту. Для стабільності можна повторити прогін 2–3 рази
і взяти середнє/мінімум.

### Крок 8. Видалення ресурсів (обов'язково!)

ВМ тарифікуються, поки працюють. Після тестів:

```bash
./deploy/delete_cluster.sh
```

Перевірка, що нічого не лишилося: `gcloud compute instances list`.

Якщо хочете лише призупинити роботу — `gcloud compute instances stop parcs-master parcs-worker-{1..6}`,
потім `start`. Внутрішні IP при цьому зберігаються, а зовнішня IP майстра зміниться —
нову дивіться в `gcloud compute instances list`.

## Завантаження коду на GitHub

```bash
git init
git add factorization.py bench.py inputs deploy README.md .gitignore results.csv
git commit -m "PARCS-Python: trial division factorization"
git branch -M main
git remote add origin https://github.com/<ваш-логін>/parcs-factorization.git
git push -u origin main
```

(Спершу створіть порожній репозиторій `parcs-factorization` на github.com.)

## Посилання

* PARCS-Python: <https://github.com/Hummer12007/parcs-python>, образ <https://hub.docker.com/r/hummer12007/parcs-node>
* Вимкнення агента запуску контейнерів: <https://docs.cloud.google.com/compute/docs/deprecations/container-startup-agent-on-compute>
* Умови free trial Google Cloud: <https://cloud.google.com/terms/trial>
