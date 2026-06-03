# Topic 142: Self-Tuning Distributed DB - Query Predictor

## Đề Tài

Xây dựng hệ thống cơ sở dữ liệu phân tán có khả năng tự điều chỉnh bằng Markov Chain bậc 2.

## Dataset

`Query_History_Logs`

## Nhiệm Vụ

- Train Markov Chain bậc 2 để dự đoán next query.
- Dựa trên prediction, hệ thống pre-fetch dữ liệu vào Redis.
- Đo mức tăng cache hit rate.
- So sánh query response time khi có và không có AI pre-fetching.

## Cách Chạy
```powershell
docker-compose up -d
pip install -r requirements.txt
python main.py setup
python main.py genlogs
python main.py train
python main.py benchmark
python main.py report
```
