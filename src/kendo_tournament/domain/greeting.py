"""책자 앞표지 다음 쪽의 「대회사」: 사진 · 본문 · 오른쪽 아래 날짜·직함·이름. 틀은 그대로 두고 내용만 고친다.

참고 책자(제26회 광명시장기 카탈로그 2쪽)를 따른다. 기본 본문은 그 책자의 글이다(운영자 단체가 직접 만든 책자).
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BODY = """만물이 생동하는 희망찬 봄날, 검도 대회를 성황리에 개최하게 된 것을 매우 기쁘게 생각하며, 검도 가족 여러분과 함께 진심으로 축하합니다.

검도는 단순한 신체 단련을 넘어, 예를 중시하고 올바른 마음가짐과 강인한 정신력을 배양하는 훌륭한 무예입니다. '교검지애'라는 말처럼, 검을 나누며 서로를 존중하고 배려하는 마음을 배우는 것이야말로 검도가 가진 진정한 가치일 것입니다.

오늘 대회에 참가하신 선수 여러분! 그동안 도장에서 사범님들의 가르침 아래 갈고닦은 기량을 오늘 이 자리에서 유감없이 발휘하시길 바랍니다. 승패에 지나치게 집착하기보다는, 상대방을 존중하며 정정당당하게 겨루는 진정한 검도인의 자세를 보여주시기를 당부드립니다.

무엇보다 단 한 명의 부상자도 없이 모두가 안전하게 대회를 마무리하기를 바라며 끝으로, 대회 준비를 위해 애써주신 모든 분들의 노고에 다시 한번 감사드립니다. 감사합니다."""
DEFAULT_POSITION = "광명시 검도회장"


@dataclass(frozen=True)
class Greeting:
    """photo_file 은 사진 파일 경로(비면 사진 없이 글만), date_text 가 비면 대회 날짜를 쓴다. 본문의 빈 줄은 문단 나눔이다."""

    body: str = DEFAULT_BODY
    date_text: str = ""
    position: str = DEFAULT_POSITION
    name: str = ""
    photo_file: str = ""

    def paragraphs(self) -> list[str]:
        return [part.strip() for part in self.body.split("\n\n") if part.strip()]


@dataclass(frozen=True)
class Photo:
    """사진 한 장(대회사 사진 · 표지 배경). png 칸에는 PNG 나 JPG 바이트가 든다. aspect 는 가로÷세로."""

    png: bytes
    aspect: float


DEFAULT_GREETING = Greeting()
