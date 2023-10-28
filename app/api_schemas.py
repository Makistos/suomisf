""" API schemas. """
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
                "alt_name": {"type": ["string", "null"]},
                "fullname": {"type": ["string", "null"]},
                "other_names": {"type": ["string", "null"]},
                "first_name": {"type": ["string", "null"]},
                "last_name": {"type": ["string", "null"]},
                "image_src": {"type": ["string", "null"]},
                "dob": {"type": ["integer", "string", "null"]},
                "dod": {"type": ["integer", "string", "null"]},
                "bio": {"type": ["string", "null"]},
                "bio_src": {"type": ["string", "null"]},
                "nationality": {
                  "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "id": {"type": ["integer", "null"]},
                            "name": {"type": "string"},
                        }
                    },
                    {
                      "type": ["string", "null"]
                    }
                  ]
                },
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": ["integer", "null"]},
                            "link": {"type": "string"},
                            "description": {"type": ["string", "null"]},
                        },
                        "required": ["link"],
                    }
                },
                "aliases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": ["integer", "null"]},
                            "name": {"type": ["string", "null"]},
                        },
                    }
                }
            },
            "required": ["name"],
        }
    }
}
