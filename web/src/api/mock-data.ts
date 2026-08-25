// 이 파일은 손으로 고치지 않습니다.
// agent-ux/export_web_mock.py 가 실제 실행 기록에서 뽑아 씁니다.
//   python export_web_mock.py --clean <run_id> --buggy <run_id>

export const MOCK_DATA = {
  "generatedAt": "2026-08-25T20:28:20",
  "goal": "코튼 셔츠를 장바구니에 담아 주문까지 마친다",
  "startPath": "/index.html",
  "axes": {
    "literacy": "숙련도",
    "attention": "주의 지속",
    "patience": "인내심",
    "breadth": "탐색 범위"
  },
  "axisDistribution": {
    "literacy": {
      "1": 20,
      "2": 20,
      "3": 20,
      "4": 20,
      "5": 20
    },
    "attention": {
      "1": 20,
      "2": 20,
      "3": 20,
      "4": 20,
      "5": 20
    },
    "patience": {
      "1": 20,
      "2": 20,
      "3": 20,
      "4": 20,
      "5": 20
    },
    "breadth": {
      "1": 20,
      "2": 20,
      "3": 20,
      "4": 20,
      "5": 20
    }
  },
  "personaTotal": 100,
  "maps": {
    "clean": {
      "pages": [
        {
          "path": "/index.html",
          "title": "MOJI STORE — 기본에 충실한 옷",
          "layout": "상단 띠 배너와 로고, 카테고리 메뉴, 장바구니 버튼이 헤더에 배치되어 있고, 메인 히어로 섹션 아래에 인기 상품 목록 카드들이 나열되어 있습니다."
        },
        {
          "path": "/product.html?id=3",
          "title": "미니멀 레더 스니커즈 — MOJI STORE",
          "layout": "상단에 로고와 카테고리 네비게이션이 있고, 중앙 좌측에는 상품 이미지 영역, 우측에는 상품명, 가격, 옵션 선택(색상, 사이즈), 수량 조절 버튼, 장바구니/바로구매 버튼이 배치되어 있습니다. 하단에는 상품 설명 및 가이드 등의 상세 영역이 위치합니다."
        },
        {
          "path": "/cart.html",
          "title": "장바구니 — MOJI STORE",
          "layout": "상단에 브랜드 로고와 카테고리 메뉴, 장바구니 아이콘이 배치되어 있고, 좌측 영역에는 담은 상품 목록과 수량 조절 및 삭제 버튼이 위치하며, 우측 영역에는 결제 예상 금액 요약 및 결제하기 버튼이 배치된 구조입니다."
        },
        {
          "path": "/checkout.html",
          "title": "주문/결제 — MOJI STORE",
          "layout": "상단에 내비게이션 바와 주문 진행 단계가 위치하고, 좌측에는 주문 방식, 주문자 정보, 배송지 및 결제 수단 입력 양식이 있으며 우측에는 주문 요약 정보와 장바구니 돌아가기 링크가 위치합니다."
        },
        {
          "path": "/complete.html",
          "title": "주문이 완료되었습니다 — MOJI STORE",
          "layout": "상단에 로고와 메뉴, 장바구니 링크가 표시되고 중앙에 주문 완료 메시지, 주문 요약 정보 카드, 주문 상세 보기 및 쇼핑 계속하기 버튼이 배치되어 있습니다."
        },
        {
          "path": "/list.html?cat=%EC%A0%84%EC%B2%B4&sort=popular",
          "title": "전체 상품 — MOJI STORE",
          "layout": "상단에 네비게이션 메뉴와 장바구니가 있고, 중앙에는 카테고리 필터 버튼과 정렬 드롭다운, 하단에 상품 카드가 그리드 형태로 배열된 상품 목록 화면입니다."
        }
      ],
      "steps": 12,
      "shots": 12,
      "usd": 0.036357
    },
    "buggy": {
      "pages": [
        {
          "path": "/index.html",
          "title": "쇼핑몰",
          "layout": "상단에는 브랜드 로고, 카테고리 메뉴, 장바구니 링크가 배치되어 있고, 중앙에는 이벤트 배너와 인기상품 및 신상품 카드가 Grid 형태로 나열된 메인 화면입니다."
        },
        {
          "path": "/list.html",
          "title": "쇼핑몰",
          "layout": "상단에 로고와 카테고리 메뉴, cart 링크가 위치하며, 그 아래로 카테고리 필터 버튼과 상품 목록 그리드가 배치되어 있는 화면입니다. 하단에는 푸터 링크가 위치합니다."
        },
        {
          "path": "/product.html?id=1",
          "title": "쇼핑몰",
          "layout": "상단에는 메뉴와 장바구니 링크가 배치되어 있으며, 좌측에는 대형 상품 이미지, 우측에는 상품 정보, 옵션 선택 버튼, 수량 입력란, 확인/구매 버튼 및 설명글이 영역을 분할하고 하단에는 관련 상품과 푸터 링크가 존재합니다."
        },
        {
          "path": "/cart.html",
          "title": "쇼핑몰",
          "layout": "상단에 로고와 카테고리 네비게이션 바가 있고, 중앙에는 장바구니 상품 목록 표와 수량 변경 요소, 하단에는 합계 금액과 확인 링크가 배치되어 있습니다."
        },
        {
          "path": "/checkout.html",
          "title": "쇼핑몰",
          "layout": "상단 내비게이션 바 아래에 주문을 위한 회원가입 폼(이름, 연락처, 이메일, 비밀번호, 주소 입력 칸 및 약관 동의 체크박스)이 위치하고, 오른쪽 하단에 결제금액과 확인 버튼이 배치된 화면입니다."
        },
        {
          "path": "/complete.html",
          "title": "쇼핑몰",
          "layout": "상단에는 로고와 홈, 전체, 장바구니 링크가 배치되어 있고, 본문 영역에는 주문 접수 완료 문구와 주문 금액이 표시되며, 하단에는 약관 및 고객센터 링크가 위치합니다."
        }
      ],
      "steps": 31,
      "shots": 31,
      "usd": 0.088871
    }
  },
  "runs": {
    "clean": {
      "runId": "final_clean10",
      "variant": "clean",
      "usage": {
        "calls": 124,
        "tokens_in": 190852,
        "tokens_out": 5694,
        "cost_usd": 0.164491,
        "by_model": {
          "gemini-3.6-flash": {
            "in": 190852,
            "out": 5694
          }
        }
      },
      "personas": [
        {
          "id": "P001",
          "label": "숙련3·주의3·인내4·탐색3",
          "traits": {
            "literacy": 3,
            "attention": 3,
            "patience": 4,
            "breadth": 3
          },
          "steps": 12,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 '상의' 카테고리로 이동합니다.",
          "lastThought": "주문이 정상적으로 완료되었으므로 목표를 달성하였습니다."
        },
        {
          "id": "P002",
          "label": "숙련1·주의1·인내3·탐색2",
          "traits": {
            "literacy": 1,
            "attention": 1,
            "patience": 3,
            "breadth": 2
          },
          "steps": 13,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 일단 상의 카테고리를 눌러봅니다.",
          "lastThought": "주문 완료 페이지에 도착하여 코튼 셔츠 주문이 성공적으로 끝났습니다."
        },
        {
          "id": "P003",
          "label": "숙련2·주의2·인내2·탐색2",
          "traits": {
            "literacy": 2,
            "attention": 2,
            "patience": 2,
            "breadth": 2
          },
          "steps": 13,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 들어가 봅니다.",
          "lastThought": "주문이 정상적으로 완료되었음을 확인했습니다. 목표를 달성했으므로 쇼핑을 마칩니다."
        },
        {
          "id": "P004",
          "label": "숙련1·주의4·인내5·탐색5",
          "traits": {
            "literacy": 1,
            "attention": 4,
            "patience": 5,
            "breadth": 5
          },
          "steps": 16,
          "end": "loop_detected",
          "endLabel": "맴돌다 중단",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "배송지 입력 정보를 수정하기 위해 화면 위로 다시 올라갑니다."
        },
        {
          "id": "P005",
          "label": "숙련5·주의4·인내5·탐색4",
          "traits": {
            "literacy": 5,
            "attention": 4,
            "patience": 5,
            "breadth": 4
          },
          "steps": 13,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리 메뉴로 이동합니다.",
          "lastThought": "주문이 정상적으로 완료되었으므로 목표를 성공적으로 달성했습니다."
        },
        {
          "id": "P006",
          "label": "숙련1·주의2·인내5·탐색5",
          "traits": {
            "literacy": 1,
            "attention": 2,
            "patience": 5,
            "breadth": 5
          },
          "steps": 13,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 '상의' 카테고리를 클릭해 상품들을 살펴봅니다.",
          "lastThought": "주문 완료 페이지에 도달하여 코튼 셔츠의 주문이 최종 완료되었으므로 목표를 달성했습니다."
        },
        {
          "id": "P007",
          "label": "숙련5·주의1·인내2·탐색2",
          "traits": {
            "literacy": 5,
            "attention": 1,
            "patience": 2,
            "breadth": 2
          },
          "steps": 15,
          "end": "gave_up",
          "endLabel": "포기",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "우편번호와 주소를 입력하는 칸이 화면 조작 요소에 보이지 않아 결제를 진행할 수 없습니다. 더 이상 진행할 수 없으니 포기합니다."
        },
        {
          "id": "P008",
          "label": "숙련4·주의5·인내2·탐색3",
          "traits": {
            "literacy": 4,
            "attention": 5,
            "patience": 2,
            "breadth": 3
          },
          "steps": 5,
          "end": "loop_detected",
          "endLabel": "맴돌다 중단",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동해보겠습니다.",
          "lastThought": "상품 옵션(색상, 사이즈) 및 장바구니 버튼을 누르기 위해 화면 위쪽으로 스크롤하여 이동하겠습니다."
        },
        {
          "id": "P009",
          "label": "숙련5·주의5·인내5·탐색4",
          "traits": {
            "literacy": 5,
            "attention": 5,
            "patience": 5,
            "breadth": 4
          },
          "steps": 12,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾아 주문하기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "주문 완료 페이지에 도달하여 코튼 셔츠 주문이 정상적으로 완료되었음을 확인했습니다. 목표를 달성했으므로 종료합니다."
        },
        {
          "id": "P010",
          "label": "숙련5·주의5·인내2·탐색5",
          "traits": {
            "literacy": 5,
            "attention": 5,
            "patience": 2,
            "breadth": 5
          },
          "steps": 12,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "코튼 셔츠 주문이 완료되었으므로 목표를 성공적으로 달성했습니다."
        }
      ]
    },
    "buggy": {
      "runId": "final_buggy10",
      "variant": "buggy",
      "usage": {
        "calls": 30,
        "tokens_in": 56104,
        "tokens_out": 1565,
        "cost_usd": 0.047947,
        "by_model": {
          "gemini-3.6-flash": {
            "in": 56104,
            "out": 1565
          }
        }
      },
      "personas": [
        {
          "id": "P001",
          "label": "숙련3·주의3·인내4·탐색3",
          "traits": {
            "literacy": 3,
            "attention": 3,
            "patience": 4,
            "breadth": 3
          },
          "steps": 21,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리 메뉴로 이동합니다.",
          "lastThought": "주문이 완료되어 주문 접수 화면이 보입니다. 목표인 코튼 셔츠 주문을 성공적으로 마쳤으므로 작업을 완료합니다."
        },
        {
          "id": "P002",
          "label": "숙련1·주의1·인내3·탐색2",
          "traits": {
            "literacy": 1,
            "attention": 1,
            "patience": 3,
            "breadth": 2
          },
          "steps": 19,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 우선 상의 카테고리를 눌러봅니다.",
          "lastThought": "주문 접수 완료 화면이 표시되었으므로 목표를 달성했습니다."
        },
        {
          "id": "P003",
          "label": "숙련2·주의2·인내2·탐색2",
          "traits": {
            "literacy": 2,
            "attention": 2,
            "patience": 2,
            "breadth": 2
          },
          "steps": 17,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "주문 접수 완료 화면에 도달하여 주문이 성공적으로 마쳐졌으므로 목표를 달성했습니다."
        },
        {
          "id": "P004",
          "label": "숙련1·주의4·인내5·탐색5",
          "traits": {
            "literacy": 1,
            "attention": 4,
            "patience": 5,
            "breadth": 5
          },
          "steps": 23,
          "end": "gave_up",
          "endLabel": "포기",
          "firstThought": "코튼 셔츠를 찾기 위해 우선 상의 카테고리로 이동해보겠습니다.",
          "lastThought": "화면 전체를 덮고 있는 팝업 레이어 때문에 약관 동의 체크박스와 확인 버튼 등 대부분의 요소가 전혀 클릭되지 않고, 스크롤도 되지 않아 더 이상 진행할 수 없습니다."
        },
        {
          "id": "P005",
          "label": "숙련5·주의4·인내5·탐색4",
          "traits": {
            "literacy": 5,
            "attention": 4,
            "patience": 5,
            "breadth": 4
          },
          "steps": 23,
          "end": "gave_up",
          "endLabel": "포기",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동해 보겠습니다.",
          "lastThought": "이용약관 동의 체크박스와 결제 확인 버튼이 화면 전체를 덮는 레이어에 가려져 눌리지 않고, 더 이상 진행할 수 있는 방법이 없습니다."
        },
        {
          "id": "P006",
          "label": "숙련1·주의2·인내5·탐색5",
          "traits": {
            "literacy": 1,
            "attention": 2,
            "patience": 5,
            "breadth": 5
          },
          "steps": 7,
          "end": "loop_detected",
          "endLabel": "맴돌다 중단",
          "firstThought": "코튼 셔츠를 찾기 위해 '상의' 카테고리로 이동해 보겠습니다.",
          "lastThought": "사이즈 선택을 위해 M 사이즈 버튼을 눌러보겠습니다."
        },
        {
          "id": "P007",
          "label": "숙련5·주의1·인내2·탐색2",
          "traits": {
            "literacy": 5,
            "attention": 1,
            "patience": 2,
            "breadth": 2
          },
          "steps": 10,
          "end": "gave_up",
          "endLabel": "포기",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "회원가입 양식이 복잡하고 잘 진행되지 않아 포기하고 나갑니다."
        },
        {
          "id": "P008",
          "label": "숙련4·주의5·인내2·탐색3",
          "traits": {
            "literacy": 4,
            "attention": 5,
            "patience": 2,
            "breadth": 3
          },
          "steps": 6,
          "end": "gave_up",
          "endLabel": "포기",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리 메뉴로 이동하겠습니다.",
          "lastThought": "팝업 백드롭 레이어 때문에 상품 클릭이 되지 않고, 팝업 닫기/확인 버튼도 제대로 작동하지 않아 더 이상 진행하기 어렵습니다."
        },
        {
          "id": "P009",
          "label": "숙련5·주의5·인내5·탐색4",
          "traits": {
            "literacy": 5,
            "attention": 5,
            "patience": 5,
            "breadth": 4
          },
          "steps": 24,
          "end": "goal_reached",
          "endLabel": "달성",
          "firstThought": "코튼 셔츠를 찾기 위해 상의 카테고리로 이동합니다.",
          "lastThought": "주문 접수 완료 화면에 도달하여 코튼 셔츠 주문이 정상적으로 마쳐졌습니다. 목표를 달성했으므로 종료합니다."
        },
        {
          "id": "P010",
          "label": "숙련5·주의5·인내2·탐색5",
          "traits": {
            "literacy": 5,
            "attention": 5,
            "patience": 2,
            "breadth": 5
          },
          "steps": 8,
          "end": "gave_up",
          "endLabel": "포기",
          "firstThought": "코튼 셔츠를 찾기 위해 '상의' 카테고리로 이동해 보겠습니다.",
          "lastThought": "팝업 레이어로 인해 상품을 클릭할 수 없고 닫기 버튼과 확인 버튼도 작동하지 않아 더 이상 진행이 어렵습니다. 구매 시도를 중단합니다."
        }
      ]
    }
  },
  "measured": {
    "calls": 154,
    "tokensIn": 246956,
    "tokensOut": 7259,
    "usd": 0.2124,
    "usdPerPersona": 0.0106,
    "note": "실제 실행에서 측정한 값입니다. 추정식이 아닙니다."
  }
}
