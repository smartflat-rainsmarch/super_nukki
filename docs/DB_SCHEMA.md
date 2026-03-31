# Database Schema

## users
- id (PK)
- email
- password
- plan_type
- created_at

## projects
- id (PK)
- user_id (FK)
- image_url
- status (pending, processing, done, failed)
- created_at

## layers
- id (PK)
- project_id (FK)
- type (text, button, image, background)
- position (json)
- image_url
- text_content
- z_index

## jobs
- id (PK)
- project_id
- status
- started_at
- finished_at

## billing
- id
- user_id
- plan
- usage_count
- reset_date