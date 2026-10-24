"""Computed column profiles over the bounded local dataset representation."""
from collections import Counter
from math import sqrt


def percentile(sorted_values, fraction):
    position = (len(sorted_values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def profile_dataset(dataset_row):
    records = dataset_row["records_json"]
    schema = dataset_row["schema_json"]
    import json
    records = json.loads(records) if isinstance(records, str) else records
    schema = json.loads(schema) if isinstance(schema, str) else schema
    row_count = dataset_row["row_count"]
    profiles = []
    for column in schema:
        name, kind = column["name"], column["type"]
        values = [row[name] for row in records if row[name] is not None]
        item = {"name": name, "type": kind, "nullable": column["nullable"],
                "null_count": row_count - len(values), "distinct_count": len(set(values))}
        if values:
            counts = Counter(values)
            item["top_values"] = [{"value": value, "count": count} for value, count in counts.most_common(5)]
        if kind in ("integer", "number") and values:
            nums = sorted(float(value) for value in values)
            mean = sum(nums) / len(nums)
            variance = sum((value - mean) ** 2 for value in nums) / len(nums)
            q1, q3 = percentile(nums, 0.25), percentile(nums, 0.75)
            lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            item.update(min=nums[0], max=nums[-1], mean=round(mean, 3),
                        standard_deviation=round(sqrt(variance), 3),
                        outlier_count=sum(value < lower or value > upper for value in nums))
        elif kind == "string" and values:
            lengths = [len(value) for value in values]
            item.update(min_length=min(lengths), max_length=max(lengths),
                        mean_length=round(sum(lengths) / len(lengths), 2))
        elif kind == "boolean" and values:
            item["true_count"] = sum(value.casefold() == "true" for value in values)
            item["false_count"] = len(values) - item["true_count"]
        elif kind in ("date", "timestamp") and values:
            item.update(earliest=min(values), latest=max(values))
        profiles.append(item)
    return {"row_count": row_count, "columns": profiles}
