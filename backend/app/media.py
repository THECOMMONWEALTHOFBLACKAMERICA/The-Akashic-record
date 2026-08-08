from dataclasses import dataclass

@dataclass
class MediaResult:
    provider: str
    media_type: str
    uri: str
    metadata: dict

class ImageProvider:
    async def generate(self,prompt:str,**kwargs)->MediaResult:
        raise NotImplementedError

class VideoProvider:
    async def generate(self,prompt:str,**kwargs)->MediaResult:
        raise NotImplementedError

# Provider adapters belong behind these interfaces. Do not hard-code fictional Sora/Veo endpoints.
# Production adapters should implement submit -> poll -> download, retries, quotas, moderation, and provenance metadata.
