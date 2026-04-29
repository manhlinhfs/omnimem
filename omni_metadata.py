import datetime


def current_timestamp():
    return datetime.datetime.utcnow().isoformat(timespec="microseconds")


def _normalize_datetime(parsed_datetime):
    if parsed_datetime.tzinfo is not None:
        parsed_datetime = parsed_datetime.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return parsed_datetime


def _parse_datetime_like(value, upper_bound=False):
    raw = str(value).strip()
    if not raw:
        raise RuntimeError("Time filter value cannot be empty.")

    if "T" not in raw:
        try:
            parsed_date = datetime.date.fromisoformat(raw)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid date '{value}'. Use YYYY-MM-DD or an ISO-8601 datetime."
            ) from exc

        if upper_bound:
            return datetime.datetime.combine(parsed_date, datetime.time.max)
        return datetime.datetime.combine(parsed_date, datetime.time.min)

    normalized_raw = raw.replace("Z", "+00:00")
    try:
        parsed_datetime = datetime.datetime.fromisoformat(normalized_raw)
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid datetime '{value}'. Use YYYY-MM-DD or an ISO-8601 datetime."
        ) from exc

    return _normalize_datetime(parsed_datetime)


def coerce_metadata_value(value):
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def normalize_tags(tags):
    if not tags:
        return None

    parts = sorted({part.strip().lower() for part in str(tags).split(",") if part.strip()})
    if not parts:
        return None
    return ",".join(parts)


def normalize_mime_type(mime_type):
    if mime_type is None:
        return None
    normalized = str(mime_type).strip().lower()
    return normalized or None


def build_base_metadata(source, timestamp=None, tags=None, **extra):
    normalized_timestamp = timestamp or current_timestamp()
    metadata = {
        "source": str(source).strip(),
        "timestamp": normalized_timestamp,
        "timestamp_epoch": int(_parse_datetime_like(normalized_timestamp).timestamp()),
    }

    normalized_tags = normalize_tags(tags)
    if normalized_tags:
        metadata["tags"] = normalized_tags

    for key, value in extra.items():
        if value is None:
            continue
        metadata[key] = coerce_metadata_value(value)

    return metadata


def parse_time_filter(value, upper_bound=False):
    return _parse_datetime_like(value, upper_bound=upper_bound).isoformat(timespec="microseconds")


def build_search_where(source=None, mime_type=None):
    clauses = []

    normalized_source = str(source).strip() if source else None
    if normalized_source:
        clauses.append({"source": normalized_source})

    normalized_mime_type = normalize_mime_type(mime_type)
    if normalized_mime_type:
        clauses.append({"mime_type": normalized_mime_type})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def build_time_bounds(since=None, until=None):
    lower_bound = parse_time_filter(since, upper_bound=False) if since else None
    upper_bound = parse_time_filter(until, upper_bound=True) if until else None
    return lower_bound, upper_bound


def metadata_matches_time_bounds(metadata, lower_bound=None, upper_bound=None):
    if lower_bound is None and upper_bound is None:
        return True

    timestamp = metadata.get("timestamp")
    if not timestamp:
        return False

    normalized_timestamp = parse_time_filter(timestamp)
    if lower_bound is not None and normalized_timestamp < lower_bound:
        return False
    if upper_bound is not None and normalized_timestamp > upper_bound:
        return False
    return True


def describe_search_filters(source=None, since=None, until=None, mime_type=None):
    parts = []
    if source:
        parts.append(f"source={str(source).strip()}")
    if since:
        parts.append(f"since={str(since).strip()}")
    if until:
        parts.append(f"until={str(until).strip()}")
    normalized_mime_type = normalize_mime_type(mime_type)
    if normalized_mime_type:
        parts.append(f"mime_type={normalized_mime_type}")
    return parts
