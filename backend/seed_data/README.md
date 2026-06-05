# Seed Data Guide

## How to run

1. Ensure the MySQL database `sales_training` exists:

   ```sql
   CREATE DATABASE IF NOT EXISTS sales_training DEFAULT CHARACTER SET utf8mb4;
   ```

2. Run migrations (first time):

   ```bash
   cd backend
   alembic upgrade head
   ```

3. Run the seeder:

   ```bash
   cd backend
   python -m seed_data.seed_all
   ```

## What gets created

- **Product categories** — 7 categories with codes: qingkong, xieruoshi, jiaosu, yanjiang, zhoubian, gongneng, qiwenhua
- **Stores** — HQ (总部), FLAGSHIP (旗舰店)
- **Admin user** — username: `admin`, password: `admin123` (super_admin role)

## Notes

- The seeder is idempotent — running it multiple times will not create duplicates.
- Passwords are hashed with bcrypt.
- All timestamps use UTC.
