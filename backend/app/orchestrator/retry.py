def should_retry(retry_count: int, max_retries: int) -> bool:
    return retry_count < max_retries

