# AI Investigation Engine

Multi-hop RAG სისტემა დოკუმენტურ კოლექციაზე: პოულობს ინფორმაციას რამდენიმე წყაროდან,
აკავშირებს ფაქტებს, პასუხს ციტატებით აძლევს, აფიქსირებს ურთიერთგამომრიცხავ წყაროებს და
არასაკმარისი მტკიცებულების დროს უარს ამბობს პასუხზე (ფაქტებს არ იგონებს).

- **Live demo:** TODO (Render URL)
- **Repo:** https://github.com/rekhviashvili2005/investigation-engine

> Free tier-ის შენიშვნა: აპლიკაცია Render-ის უფასო ტარიფზეა და უმოქმედობისას იძინებს.
> პირველი გახსნა ~1 წუთს შეიძლება გასტანდეს. პასუხი 0.1 CPU-ზე და LLM-ის რამდენიმე გამოძახების გამო
> რამდენიმე წამი-ათეული წამია.

## არქიტექტურა

```
 Upload / Dataset                    Question
      │                                  │
 parsers (txt, md, html, pdf, json)   decompose (LLM)
      │                                  │
 chunking (sentence | fixed)         agent loop: LLM --tool call--> search_documents
      │                                  │                              │
 dedup (hash + shingles/Jaccard)         │       dense (pgvector) + BM25 (own) -> weighted RRF -> MMR
      │                                  │                              │
 embeddings (fastembed, 384d)            +<---- numbered evidence <-----+
      │                                  │
 Neon PostgreSQL + pgvector         final JSON answer (LLM) -> validate (own code)
 (vector HNSW + tsvector GIN)       -> answered | insufficient_evidence | conflict
```

| ფენა | ფაილები |
|---|---|
| Ingestion | `app/ingestion/` (parsers, chunking, dedup, embedder, pipeline) |
| DB | `app/db/` (schema.sql, connection, repository) |
| Retrieval | `app/retrieval/` (bm25, dense, fusion, rerank, search) |
| LLM / Agent | `app/llm/` (client, prompts, tools, agent) |
| API | `app/api/` (FastAPI) |
| UI | `app/ui.py` (Streamlit) |
| Eval | `eval/` |

## RAG pipeline ეტაპობრივად

1. **Decompose:** LLM კითხვას ქვეკითხვებად ყოფს (JSON).
2. **Tool calling:** LLM თვითონ იძახებს `search_documents`-ს (ციკლი ჩვენი კოდით იმართება, max 6 ნაბიჯი).
   ყოველ ნაპოვნ chunk-ს ეძლევა ნომერი (`EvidenceStore`).
3. **Final answer:** LLM აბრუნებს JSON-ს: `status`, `answer`, `citations`, `conflicts`, `missing`.
4. **Validate (ჩვენი კოდი):** არარსებული ციტატები იგდება; ციტატის გარეშე `answered` გადადის
   `insufficient_evidence`-ში; `conflict` აღწერის გარეშე არ მიიღება.
5. **შეცდომები:** LLM კლიენტს აქვს retry ექსპონენციალური პაუზით (429/5xx), timeout, `LLMError`.
6. **Prompt injection:** prompt-ში retrieved ტექსტი DATA-დ არის მონიშნული (ცალკე ტესტი ბონუსად TODO).

## საკუთარი ალგორითმები (არა მზა ბიბლიოთეკა)

- **BM25** (`app/retrieval/bm25.py`): ფორმულა ხელითაა დაწერილი; GIN ინდექსი მხოლოდ კანდიდატებს არჩევს.
- **Weighted RRF** (`fusion.py`): `Σ w / (k + rank)`; dense:bm25 = 3:1.
- **MMR + per-document limit** (`rerank.py`) Jaccard-ით shingle-ებზე.
- **Dedup** (`dedup.py`): ზუსტი (SHA-256 ნორმალიზებულზე) და near-duplicate (shingle Jaccard).

## ტექნიკური არჩევანის დასაბუთება

| არჩევანი | რატომ |
|---|---|
| PostgreSQL + pgvector (Neon) | ერთ ბაზაში ვექტორი, tsvector და მეტამონაცემი; უფასო; მონაცემები რესტარტის შემდეგ რჩება |
| fastembed `bge-small-en-v1.5` | უფასო, პატარა (CPU-ზე მუშაობს), 384 განზომილება |
| Gemini (`gemini-flash-lite-latest`) | უფასო ტარიფი, tool calling; `gemini-3.8-flash` 504 შეცდომებს იძლეოდა |
| Streamlit პირდაპირ მოდულებზე | Render-ის 512 MB-ზე ერთი პროცესი (FastAPI+UI ორი პროცესი არ ეტეოდა) |
| Colab მძიმე ჩატვირთვებისთვის | ლოკალური CPU ნელია; იგივე სკრიპტები, იგივე ბაზა |

## გაშვება ლოკალურად

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # შეავსე DATABASE_URL, LLM_API_KEY, LLM_MODEL
python -m scripts.init_db
python -m scripts.load_hotpotqa --questions 150
python -m streamlit run app/ui.py            # UI
python -m uvicorn app.api.main:app           # REST API (/docs)
python -m pytest -v                          # ტესტები
```

REST API: `GET /health`, `GET/POST /documents`, `DELETE /documents/{id}`, `POST /ask`.

## Deployment

Render Free Web Service (Docker, Oregon). საიდუმლოები (`DATABASE_URL`, `LLM_API_KEY`, `LLM_MODEL`)
მხოლოდ Render Environment-ში; `.env` git-ში არასოდეს. მონაცემები Neon-შია (Render-ის დისკი დროებითია).

**უფასო ტარიფის შეზღუდვები:** 512 MB RAM, 0.1 CPU, ძილი უმოქმედობისას, Neon 1 GB, Gemini-ს
მოთხოვნების ლიმიტი (retry ამუშავებს). დიდი ჩატვირთვა Colab-იდან კეთდება იმავე სკრიპტით.

## მონაცემები

- HotpotQA (distractor, validation): TODO რაოდენობა ჩატვირთვის დასრულების შემდეგ (მიზანი 50k+ პარაგრაფი)
- danluu post-mortems: 111 HTML დოკუმენტი
- სინთეზური წინააღმდეგობრივი დოკუმენტები (`synthetic://`, გამოგონილი კომპანიები)
- ატვირთვები: `upload://`

## შეფასება

დეტალები: `docs/EVALUATION.md` (TODO). მოკლედ (1490 პარაგრაფიან ბაზაზე; 50k-ზე ხელახლა გასაზომია):

| Retrieval (150 კითხვა, K=8) | Recall@8 | MRR | Full hit |
|---|---|---|---|
| dense | 0.937 | 0.950 | 0.873 |
| bm25 | 0.597 | 0.626 | 0.447 |
| hybrid 3:1 | 0.880 | 0.788 | 0.793 |

პასუხები (30 კითხვა, dense / hybrid 3:1): correctness მარტივი 0.9 / 0.9, multi-hop 0.5 / 0.6,
citation accuracy 0.75 / 0.85, abstention 0.9 / 1.0.
Conflict ტესტი: 3/3. Chunking (8 კითხვა): sentence doc_recall@5 0.812, fixed 0.75.

## შეზღუდვები

- eval ნაკრები პატარაა; სხვაობები ერთი კითხვის ფარგლებშია
- `answer_correct` სტრიქონული შედარებაა
- ჩატვირთვის დასრულებამდე რიცხვები 1490 პარაგრაფზეა