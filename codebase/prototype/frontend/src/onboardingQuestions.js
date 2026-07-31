// Exact keys/text as specified -- the backend template depends on these keys.
export const QUESTIONS = [
  {
    key: 'role',
    question: 'Công việc hiện tại của bạn gần nhất với mô tả nào?',
    options: [
      'Kỹ sư phần mềm / lập trình viên',
      'Product Manager / Product Owner',
      'Data Scientist / ML Engineer',
      'Vai trò kinh doanh, marketing, vận hành (non-technical)',
      'Sinh viên / đang tìm hiểu để chuyển ngành',
      'Khác',
    ],
  },
  {
    key: 'goal',
    question: 'Bạn học nội dung này để làm gì?',
    options: [
      'Áp dụng trực tiếp vào công việc đang làm',
      'Hiểu đủ để làm việc/trao đổi với đội kỹ thuật',
      'Đánh giá/ra quyết định đầu tư, chiến lược liên quan đến AI',
      'Tò mò, học cho biết',
      'Khác',
    ],
  },
  {
    key: 'level_ai_agent',
    question: 'Khi nghe cụm "AI Agent", điều nào mô tả đúng nhất hiểu biết của bạn?',
    options: [
      'Tôi chưa từng nghe hoặc không chắc nó khác gì so với chatbot thông thường',
      'Tôi hiểu đại khái đó là AI có thể tự ra quyết định và thực hiện nhiều bước để hoàn thành mục tiêu, nhưng chưa từng dùng hay xây thử',
      'Tôi đã từng dùng hoặc cấu hình một AI agent, hiểu cách nó gọi tool/function',
      'Tôi đã tự thiết kế/xây dựng luồng agent, hiểu rõ đánh đổi kiến trúc',
    ],
  },
  {
    key: 'level_product_ai',
    question: 'Về việc AI được tích hợp vào sản phẩm thực tế, bạn ở đâu?',
    options: [
      'Tôi chưa từng nghĩ về việc AI được đưa vào sản phẩm như thế nào, chỉ dùng như người dùng cuối',
      'Tôi hiểu sơ về khái niệm "AI-powered feature" nhưng chưa tham gia xây hay thiết kế',
      'Tôi đã tham gia thiết kế/lên yêu cầu cho một tính năng có AI',
      'Tôi đã trực tiếp phụ trách/ra quyết định kỹ thuật cho một sản phẩm AI từ đầu đến cuối',
    ],
  },
  {
    key: 'level_llm',
    question: 'Về LLM, mô tả nào đúng nhất với bạn?',
    options: [
      'Tôi biết ChatGPT/Claude là gì nhưng không rõ "LLM" nghĩa là gì',
      'Tôi hiểu LLM là mô hình dự đoán từ tiếp theo dựa trên lượng dữ liệu văn bản khổng lồ, nhưng chưa từng gọi API hay chỉnh prompt có hệ thống',
      'Tôi đã từng gọi API LLM, viết prompt, thử nghiệm với các tham số như temperature, max_tokens',
      'Tôi hiểu cơ chế bên trong (attention, tokenization, fine-tuning/RAG) và có thể giải thích lại cho người khác',
    ],
  },
  {
    key: 'level_transformer',
    question: 'Về kiến trúc Transformer (nền tảng của LLM), bạn ở mức nào?',
    options: [
      'Tôi chưa từng nghe đến khái niệm này',
      'Tôi biết đây là kiến trúc mạng nơ-ron làm nền cho các LLM hiện đại, nhưng không rõ cơ chế hoạt động',
      'Tôi hiểu đại khái cơ chế self-attention giúp mô hình "chú ý" vào các từ liên quan trong câu như thế nào',
      'Tôi hiểu chi tiết toán học (attention score, multi-head, positional encoding) và có thể triển khai/giải thích từ đầu',
    ],
  },
  {
    key: 'level_ai_production',
    question: 'Về việc triển khai AI vào môi trường sản xuất thực tế (production), bạn ở đâu?',
    options: [
      'Tôi chưa từng nghĩ đến sự khác biệt giữa "demo chạy thử" và "chạy thật cho người dùng"',
      'Tôi hiểu khái niệm rằng đưa AI vào production cần xử lý thêm về chi phí, độ trễ, giám sát, nhưng chưa từng làm',
      'Tôi đã từng tham gia đưa một tính năng AI ra môi trường thật',
      'Tôi đã trực tiếp thiết kế hệ thống production AI ở quy mô có người dùng thật',
    ],
  },
  {
    key: 'level_production_eval',
    question: 'Về việc đánh giá chất lượng đầu ra AI khi vận hành, bạn ở mức nào?',
    options: [
      'Tôi chưa từng nghĩ về việc làm sao biết một hệ thống AI "đang trả lời tốt hay tệ" một cách có hệ thống',
      'Tôi biết có các khái niệm như đánh giá tự động, đánh giá bằng con người, nhưng chưa từng thiết kế bộ đánh giá nào',
      'Tôi đã từng dùng hoặc thiết lập một số metric/eval đơn giản để theo dõi chất lượng output',
      'Tôi đã thiết kế bộ eval pipeline hoàn chỉnh cho hệ thống thật',
    ],
  },
]
