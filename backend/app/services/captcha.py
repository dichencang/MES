import base64
import hmac
import io
import secrets
from random import SystemRandom

from PIL import Image, ImageDraw, ImageFont
from redis.exceptions import RedisError

from app.services.auth import secret
from app.utils.responses import ApiError

EXPIRES_IN = 120
ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
FONT = ImageFont.load_default(size=30)
RANDOM = SystemRandom()
RATE_LIMIT = """
local time = redis.call('TIME')
local now = time[1] * 1000 + math.floor(time[2] / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60000)
if redis.call('ZCARD', KEYS[1]) >= 20 or
   redis.call('ZCOUNT', KEYS[1], '(' .. (now - 1000), '+inf') > 0 then
    return 0
end
redis.call('ZADD', KEYS[1], now, ARGV[1])
redis.call('PEXPIRE', KEYS[1], 60000)
return 1
"""


def image_data(code):
    image = Image.new("RGB", (144, 48), "#f0f4fa")
    draw = ImageDraw.Draw(image)
    for _ in range(140):
        draw.point((RANDOM.randrange(image.width), RANDOM.randrange(image.height)), fill="#a8b4c6")
    for index, character in enumerate(code):
        glyph = Image.new("RGBA", (34, 42))
        ImageDraw.Draw(glyph).text(
            (17, 21), character, font=FONT, anchor="mm",
            fill=RANDOM.choice(("#202a50", "#354e2f", "#662945", "#23475b")),
        )
        glyph = glyph.rotate(RANDOM.randint(-20, 20), Image.Resampling.BICUBIC)
        image.paste(glyph, (6 + index * 33, RANDOM.randint(1, 5)), glyph)
    draw.line([(0, 30), (48, 18), (96, 30), (143, 15)], fill="#8795ab", width=1)
    with io.BytesIO() as buffer:
        image.save(buffer, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def verification_value(captcha_id, code):
    return hmac.digest(secret().encode(), f"{captcha_id}:{code.upper()}".encode(), "sha256")


async def issue(redis, client_ip):
    captcha_id = secrets.token_urlsafe(24)
    try:
        allowed = await redis.eval(RATE_LIMIT, 1, f"mes:captcha:rate:{client_ip}", captcha_id)
        if not allowed:
            raise ApiError(429, 9003, "获取验证码过于频繁，请稍后再试")
        code = "".join(secrets.choice(ALPHABET) for _ in range(4))
        image = image_data(code)
        await redis.set(
            f"mes:captcha:answer:{captcha_id}", verification_value(captcha_id, code),
            ex=EXPIRES_IN,
        )
    except RedisError as error:
        raise ApiError(503, 9002, "暂时无法验证，请重试") from error
    return {"captchaId": captcha_id, "image": image, "expiresIn": EXPIRES_IN}


async def verify(redis, captcha_id, code):
    try:
        expected = await redis.getdel(f"mes:captcha:answer:{captcha_id}")
    except RedisError as error:
        raise ApiError(503, 9002, "暂时无法验证，请重试") from error
    if expected is None or not hmac.compare_digest(expected, verification_value(captcha_id, code)):
        raise ApiError(400, 2005, "验证码错误或已过期")
