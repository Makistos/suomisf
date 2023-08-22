BookseriesSchema = {
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "properties": {
                "id": {"type": ["integer", "null"]},
                "name": {"type": "string"},
                "orig_name": {"type": "string"},
                "important": {"type": "boolean"},
            },
            "required": ["name"],
        },
    },
}

PersonSchema = {
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "properties": {
                "id": {"type": ["integer", "null"]},
                "name": {"type": "string"},
                "alt_name": {"type": "string"},
                "fullname": {"type": "string"},
                "other_names": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "image_src": {"type": "string"},
                "dob": {"type": "integer"},
                "dod": {"type": "integer"},
                "bio": {"type": "string"},
                "bio_src": {"type": "string"},
                "nationality": {
                    "type": "object",
                    "properties": {
                        "id": {"type": ["integer", "null"]},
                        "name": {"type": "string"},
                    },
                    "required": ["id"],
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": ["integer", "null"]},
                            "link": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["link"],
                    }
                }
            },
            "required": ["name"],
        }
    }
}