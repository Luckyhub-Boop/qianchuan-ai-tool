
    const BASE_DATA = [
      { date: "2026-10-11", spend: 13825.55, gmv: 5880, orders: 35 },
      { date: "2026-10-12", spend: 16512.16, gmv: 10248, orders: 61 },
      { date: "2026-10-13", spend: 7260.43, gmv: 5208, orders: 31 },
      { date: "2026-10-14", spend: 11813.4, gmv: 9239, orders: 55 },
      { date: "2026-10-15", spend: 9339.2, gmv: 6720, orders: 40 },
      { date: "2026-10-16", spend: 6691.69, gmv: 3695.86, orders: 22 },
      { date: "2026-10-17", spend: 8400.79, gmv: 4871.6, orders: 29 }
    ];

    const ACCOUNT_CONFIGS = [
      {
        id: "fashion",
        name: "TT-申坤-赵镭老师(店播)-小学数学-自运营",
        handle: "赵镭精讲小数基本功",
        qianchuanId: "1744479430946824",
        status: "数据已同步",
        avatar: "赵",
        color: "#0b7a58",
        source: "千川全域推广",
        dataCutoff: "2026-10-17"
      }
    ];

    const ACCOUNTS = ACCOUNT_CONFIGS.map(config => ({
      ...config,
      data: BASE_DATA.map(row => ({ ...row }))
    }));

    let ACTIVE_ACCOUNT = ACCOUNTS[0];
    let ACTIVE_DATA = BASE_DATA;

    const METRICS = {
      spend: {
        label: "总消耗",
        short: "消耗",
        color: "#0b7a58",
        unit: "万元",
        decimals: 1,
        kind: "currency",
        daily: d => d.spend,
        aggregate: rows => rows.reduce((sum, d) => sum + d.spend, 0),
        display: value => value / 10000,
        note: "区间累计",
        deltaTone: "neutral"
      },
      gmv: {
        label: "成交金额",
        short: "成交",
        color: "#2b6f94",
        unit: "万元",
        decimals: 1,
        kind: "currency",
        daily: d => d.gmv,
        aggregate: rows => rows.reduce((sum, d) => sum + d.gmv, 0),
        display: value => value / 10000,
        note: "区间累计",
        deltaTone: "goodUp"
      },
      cost: {
        label: "成交订单成本",
        short: "订单成本",
        color: "#c9723c",
        unit: "元",
        decimals: 1,
        kind: "number",
        daily: d => d.spend / d.orders,
        aggregate: rows => sum(rows, "spend") / sum(rows, "orders"),
        display: value => value,
        note: "消耗 ÷ 成交订单数",
        deltaTone: "goodDown"
      },
      roi: {
        label: "ROI",
        short: "ROI",
        color: "#17231c",
        unit: "",
        decimals: 2,
        kind: "number",
        daily: d => d.gmv / d.spend,
        aggregate: rows => sum(rows, "gmv") / sum(rows, "spend"),
        display: value => value,
        note: "用户实付成交金额 ÷ 消耗",
        deltaTone: "goodUp"
      },
      orders: {
        label: "成交订单",
        short: "订单",
        color: "#8e6a2f",
        unit: "单",
        decimals: 0,
        kind: "number",
        daily: d => d.orders,
        aggregate: rows => sum(rows, "orders"),
        display: value => value,
        note: "区间累计",
        deltaTone: "goodUp"
      },
      spendRate: {
        label: "消耗速率",
        short: "消耗速率",
        color: "#5c6c62",
        unit: "万元/天",
        decimals: 2,
        kind: "currency",
        daily: d => d.spend / 10000,
        aggregate: rows => sum(rows, "spend") / rows.length / 10000,
        display: value => value,
        note: "日均消耗",
        deltaTone: "neutral"
      }
    };

    const state = {
      start: "2026-10-11",
      end: "2026-10-17",
      chartMetric: "spend",
      scope: "total",
      accountId: ACTIVE_ACCOUNT.id,
      view: "data",
      reviewTab: "monitor",
      reviewGranularity: 5,
      selectedSessionId: null,
      playerTime: 0,
      playerPlaying: false,
      playerSpeed: 1,
      activeAnnotationId: null,
      recording: true,
      recordSeconds: 2538,
      diagCapturing: true,
      diagWindow: 5,
      scriptTab: "banned",
      scriptWordQuery: "",
      scriptWordCategory: "all",
      scriptQualityAnchor: "fashion",
      scriptQualityScene: "all",
      scriptCollection: new Set(["fashion-1", "fashion-3", "home-1", "select-2"]),
      scriptCollectionVersion: "V1.8",
      scriptLiveRows: [],
      scriptLiveSourceIndex: 0,
      scriptLiveAccountId: null,
      scriptLivePaused: false,
      lowAnchor: "all",
      lowScene: "all",
      campaignDaypart: "evening",
      campaignDocs: [],
      campaignOperations: [],
      campaignLastEffect: null,
      campaignDocSeq: 0,
      campaignTick: 0,
      campaignSyncedAt: null
    };

    const MATERIALS = [
      { id: "VM-24101", accountId: "fashion", name: "秋冬冲锋衣-痛点开场", type: "视频", duration: "00:32", spend: 12840, gmv: 61889, impressions: 286000, clicks: 12480, orders: 312, completionRate: 38.6, dwellTime: 18.4, persona: { age: "25-34", region: "华东", gender: "女" } },
      { id: "VM-24102", accountId: "fashion", name: "加绒卫衣-上身对比", type: "视频", duration: "00:28", spend: 9650, gmv: 49601, impressions: 218000, clicks: 11240, orders: 268, completionRate: 41.2, dwellTime: 21.6, persona: { age: "24-30", region: "华南", gender: "女" } },
      { id: "VM-24103", accountId: "fashion", name: "羽绒服-价格锚点", type: "视频", duration: "00:36", spend: 15600, gmv: 63336, impressions: 342000, clicks: 13680, orders: 301, completionRate: 35.4, dwellTime: 16.2, persona: { age: "31-40", region: "华北", gender: "女" } },
      { id: "VM-24104", accountId: "home", name: "家居服-场景种草", type: "视频", duration: "00:31", spend: 7420, gmv: 33242, impressions: 176000, clicks: 7920, orders: 176, completionRate: 44.3, dwellTime: 24.1, persona: { age: "25-34", region: "华东", gender: "女" } },
      { id: "VM-24105", accountId: "fashion", name: "休闲裤-显瘦测试", type: "视频", duration: "00:26", spend: 5830, gmv: 25419, impressions: 138000, clicks: 5520, orders: 142, completionRate: 39.8, dwellTime: 17.8, persona: { age: "18-23", region: "华南", gender: "女" } },
      { id: "VM-24106", accountId: "select", name: "羊毛围巾-节日礼赠", type: "图片", duration: "静态", spend: 4180, gmv: 17222, impressions: 102000, clicks: 4590, orders: 98, completionRate: null, dwellTime: 9.4, persona: { age: "25-34", region: "华东", gender: "女" } },
      { id: "VM-24107", accountId: "fashion", name: "童装套装-宝妈口播", type: "视频", duration: "00:34", spend: 11200, gmv: 40768, impressions: 248000, clicks: 9920, orders: 214, completionRate: 36.7, dwellTime: 19.2, persona: { age: "31-40", region: "华中", gender: "女" } },
      { id: "VM-24108", accountId: "home", name: "保暖内衣-实验对比", type: "视频", duration: "00:29", spend: 8860, gmv: 41731, impressions: 198000, clicks: 9900, orders: 198, completionRate: 47.5, dwellTime: 26.8, persona: { age: "24-30", region: "华东", gender: "男" } },
      { id: "VM-24109", accountId: "fashion", name: "雪地靴-上脚展示", type: "视频", duration: "00:25", spend: 6740, gmv: 26421, impressions: 152000, clicks: 6080, orders: 131, completionRate: 42.1, dwellTime: 20.3, persona: { age: "25-34", region: "华北", gender: "女" } },
      { id: "VM-24110", accountId: "fashion", name: "针织开衫-一衣多穿", type: "视频", duration: "00:33", spend: 5120, gmv: 23296, impressions: 118000, clicks: 4720, orders: 118, completionRate: 43.6, dwellTime: 23.5, persona: { age: "18-23", region: "华东", gender: "女" } },
      { id: "VM-24111", accountId: "fashion", name: "运动套装-晨跑场景", type: "视频", duration: "00:27", spend: 13960, gmv: 44393, impressions: 312000, clicks: 10920, orders: 208, completionRate: 33.2, dwellTime: 14.8, persona: { age: "24-30", region: "华南", gender: "男" } },
      { id: "VM-24112", accountId: "fashion", name: "真丝衬衫-细节特写", type: "视频", duration: "00:30", spend: 4680, gmv: 17644, impressions: 96000, clicks: 4320, orders: 86, completionRate: 45.8, dwellTime: 25.2, persona: { age: "31-40", region: "华东", gender: "女" } },
      { id: "VM-24113", accountId: "fashion", name: "风衣-通勤穿搭", type: "视频", duration: "00:35", spend: 7280, gmv: 24898, impressions: 164000, clicks: 6560, orders: 124, completionRate: 37.9, dwellTime: 18.6, persona: { age: "25-34", region: "华北", gender: "女" } },
      { id: "VM-24114", accountId: "select", name: "马甲-叠穿教程", type: "视频", duration: "00:24", spend: 3920, gmv: 19130, impressions: 88000, clicks: 4224, orders: 94, completionRate: 49.2, dwellTime: 27.4, persona: { age: "18-23", region: "西南", gender: "女" } },
      { id: "VM-24115", accountId: "fashion", name: "牛仔裤-版型讲解", type: "视频", duration: "00:37", spend: 6240, gmv: 20904, impressions: 142000, clicks: 5680, orders: 108, completionRate: 34.6, dwellTime: 15.9, persona: { age: "24-30", region: "华中", gender: "男" } },
      { id: "VM-24116", accountId: "home", name: "睡衣套装-情侣场景", type: "视频", duration: "00:32", spend: 4860, gmv: 20461, impressions: 108000, clicks: 4860, orders: 102, completionRate: 40.7, dwellTime: 22.7, persona: { age: "25-34", region: "华南", gender: "女" } },
      { id: "VM-24117", accountId: "fashion", name: "冲锋衣-直播切片", type: "直播切片", duration: "01:08", spend: 10500, gmv: 31080, impressions: 226000, clicks: 9040, orders: 152, completionRate: 31.8, dwellTime: 12.6, persona: { age: "31-40", region: "华北", gender: "男" } },
      { id: "VM-24118", accountId: "select", name: "围巾-多色展示", type: "图片", duration: "静态", spend: 2860, gmv: 10525, impressions: 76000, clicks: 3040, orders: 62, completionRate: null, dwellTime: 8.2, persona: { age: "35-44", region: "华东", gender: "女" } },
      { id: "VM-24119", accountId: "fashion", name: "羽绒服-明星同款", type: "视频", duration: "00:39", spend: 16800, gmv: 47712, impressions: 386000, clicks: 15440, orders: 236, completionRate: 29.4, dwellTime: 11.4, persona: { age: "24-30", region: "华东", gender: "女" } },
      { id: "VM-24120", accountId: "home", name: "家居服-福利返场", type: "视频", duration: "00:23", spend: 5480, gmv: 25318, impressions: 126000, clicks: 6300, orders: 128, completionRate: 46.3, dwellTime: 25.6, persona: { age: "25-34", region: "华中", gender: "女" } }
    ];

    const MATERIAL_WEIGHTS = { spend: 0.2, orders: 0.5, clicks: 0.1, impressions: 0.1 };
    const MATERIAL_WEIGHT_TOTAL = 0.9;

    const LIVE_MONITORS = {
      fashion: {
        live: true,
        title: "10月16日 晚场",
        startTime: "19:30",
        recordSeconds: 2538,
        metrics: { viewers: 12840, spend: 28600, orders: 612, roi: 4.31, cvr: 3.18, dwell: 42.6 },
        bars: [
          { label: "19:30", value: 18 },
          { label: "19:40", value: 26 },
          { label: "19:50", value: 31 },
          { label: "20:00", value: 44 },
          { label: "20:10", value: 39 },
          { label: "20:20", value: 52 },
          { label: "20:30", value: 68 },
          { label: "20:40", value: 61 },
          { label: "20:50", value: 78 },
          { label: "21:00", value: 72 },
          { label: "21:10", value: 84 },
          { label: "21:20", value: 76 }
        ],
        events: [
          { time: "20:14", type: "problem", title: "转化率跌破 3%", desc: "观看人数继续上升，成交订单未同步增长，流量承接偏弱。" },
          { time: "20:32", type: "advantage", title: "爆款返场带动订单", desc: "返场款上线后 5 分钟订单快速抬升，建议保留固定返场节奏。" },
          { time: "21:06", type: "note", title: "平均停留时长回落", desc: "从 48.2 秒回落至 38.2 秒，需关注后续讲解节奏。" },
          { time: "21:28", type: "advantage", title: "面料演示拉动点击", desc: "近景面料测试带来点击率回升，可作为固定演示环节。" },
          { time: "21:46", type: "problem", title: "价格异议集中出现", desc: "评论区价格对比问题增多，需补充同价位对比话术。" }
        ]
      },
      home: {
        live: true,
        title: "10月16日 晚场",
        startTime: "19:45",
        recordSeconds: 2222,
        metrics: { viewers: 6420, spend: 14200, orders: 286, roi: 4.18, cvr: 2.94, dwell: 38.4 },
        bars: [
          { label: "19:45", value: 11 },
          { label: "19:55", value: 16 },
          { label: "20:05", value: 22 },
          { label: "20:15", value: 19 },
          { label: "20:25", value: 28 },
          { label: "20:35", value: 34 },
          { label: "20:45", value: 31 },
          { label: "20:55", value: 42 },
          { label: "21:05", value: 38 },
          { label: "21:15", value: 46 },
          { label: "21:25", value: 41 },
          { label: "21:35", value: 49 }
        ],
        events: [
          { time: "20:12", type: "advantage", title: "场景演示提升停留", desc: "卧室场景化展示后平均停留提升 6.8 秒。" },
          { time: "20:36", type: "problem", title: "尺码咨询集中", desc: "评论区连续出现尺码问题，需增加尺码表口播。" },
          { time: "20:58", type: "advantage", title: "福利款带动订单", desc: "福利款上架后订单增速明显，适合继续追投。" },
          { time: "21:18", type: "problem", title: "转化率低于基线", desc: "近 10 分钟转化率 2.61%，低于前 7 日均值。" }
        ]
      },
      select: {
        live: false,
        title: "10月16日 下午场（已结束）",
        startTime: "14:00",
        recordSeconds: 5400,
        metrics: { viewers: 3160, spend: 7600, orders: 142, roi: 3.86, cvr: 2.72, dwell: 31.8 },
        bars: [
          { label: "14:00", value: 8 },
          { label: "14:10", value: 12 },
          { label: "14:20", value: 15 },
          { label: "14:30", value: 18 },
          { label: "14:40", value: 14 },
          { label: "14:50", value: 21 },
          { label: "15:00", value: 24 },
          { label: "15:10", value: 19 },
          { label: "15:20", value: 22 },
          { label: "15:30", value: 17 },
          { label: "15:40", value: 20 },
          { label: "15:50", value: 16 }
        ],
        events: [
          { time: "14:22", type: "advantage", title: "多色展示吸引点击", desc: "多色围巾展示带来点击率提升。" },
          { time: "14:48", type: "problem", title: "价格对比不足", desc: "评论区反复询问与同类商品差价，承接不足。" },
          { time: "15:12", type: "advantage", title: "礼赠场景有效", desc: "节日礼赠场景带来一波集中成交。" },
          { time: "15:36", type: "problem", title: "停留时长下滑", desc: "后段讲解节奏变慢，平均停留降至 26 秒。" }
        ]
      }
    };

    const REVIEW_SESSIONS = [
      {
        id: "fs-1016-pm",
        accountId: "fashion",
        date: "2026-10-16",
        title: "10月16日 晚场",
        startTime: "19:30",
        durationSeconds: 8320,
        summary: "本场优势在于爆款返场和面料演示，问题集中在 20:14-20:40 的流量承接与价格异议。建议下场把价格对比话术前置，并把爆款返场节奏固定到每 40 分钟一次。",
        annotations: [
          { id: "fs-1", time: 1100, type: "problem", title: "开场流量承接偏弱", desc: "前 20 分钟观看人数上升，但成交订单增长缓慢。" },
          { id: "fs-2", time: 1625, type: "problem", title: "转化率跌破 3%", desc: "观看人数继续上升，订单未同步增长，流量结构可能偏泛。" },
          { id: "fs-3", time: 2490, type: "advantage", title: "爆款返场带动订单", desc: "返场款上线后 5 分钟订单快速抬升，节奏有效。" },
          { id: "fs-4", time: 3730, type: "advantage", title: "面料演示拉高停留", desc: "近景面料测试让平均停留提升到 47 秒。" },
          { id: "fs-5", time: 5205, type: "problem", title: "价格异议集中出现", desc: "评论区出现同价位对比问题，影响后段转化。" },
          { id: "fs-6", time: 7260, type: "advantage", title: "限时福利促成成交", desc: "限时福利讲解后形成一波集中成交，可固化为收尾动作。" }
        ]
      },
      {
        id: "fs-1015-noon",
        accountId: "fashion",
        date: "2026-10-15",
        title: "10月15日 午场",
        startTime: "12:00",
        durationSeconds: 6132,
        summary: "午场开场福利有效，但中段转化率回落明显。上身对比和返场款表现较好，后续可减少中段重复讲解。",
        annotations: [
          { id: "fs-7", time: 720, type: "advantage", title: "开场福利拉高在线", desc: "开场福利款让在线人数快速达到峰值。" },
          { id: "fs-8", time: 1560, type: "problem", title: "中段转化率回落", desc: "重复讲解导致停留和订单同步下滑。" },
          { id: "fs-9", time: 2700, type: "advantage", title: "上身对比提升点击", desc: "对比展示让素材点击率回升。" },
          { id: "fs-10", time: 4020, type: "problem", title: "库存讲解不清", desc: "评论区连续询问库存和尺码，影响成交效率。" },
          { id: "fs-11", time: 5400, type: "advantage", title: "返场款集中成交", desc: "返场款在收尾阶段贡献了本场主要订单。" }
        ]
      },
      {
        id: "home-1016-pm",
        accountId: "home",
        date: "2026-10-16",
        title: "10月16日 晚场",
        startTime: "19:45",
        durationSeconds: 6840,
        summary: "场景化演示和福利款是主要优势，尺码咨询与后段转化率下滑是主要问题。建议固定尺码讲解节点，并在后段增加福利款返场。",
        annotations: [
          { id: "home-1", time: 900, type: "advantage", title: "场景演示提升停留", desc: "卧室场景展示让平均停留提升 6.8 秒。" },
          { id: "home-2", time: 2100, type: "problem", title: "尺码问题集中", desc: "尺码咨询密集出现，需要提前准备尺码表口播。" },
          { id: "home-3", time: 3300, type: "advantage", title: "福利款带动订单", desc: "福利款上架后订单增速明显。" },
          { id: "home-4", time: 4800, type: "problem", title: "转化率低于基线", desc: "近 10 分钟转化率 2.61%，低于前 7 日均值。" },
          { id: "home-5", time: 6120, type: "advantage", title: "返场组合成交", desc: "组合装返场后形成一波集中成交。" }
        ]
      },
      {
        id: "select-1016-noon",
        accountId: "select",
        date: "2026-10-16",
        title: "10月16日 下午场",
        startTime: "14:00",
        durationSeconds: 5400,
        summary: "多色展示和礼赠场景有效，但价格对比与后段节奏是明显短板。建议下场提前准备同价位对比，并缩短后段重复讲解。",
        annotations: [
          { id: "select-1", time: 600, type: "advantage", title: "多色展示吸引点击", desc: "多色围巾展示带来点击率提升。" },
          { id: "select-2", time: 1800, type: "problem", title: "价格对比不足", desc: "评论区反复询问与同类商品差价。" },
          { id: "select-3", time: 3120, type: "advantage", title: "礼赠场景有效", desc: "节日礼赠场景带来一波集中成交。" },
          { id: "select-4", time: 4500, type: "problem", title: "停留时长下滑", desc: "后段讲解节奏变慢，平均停留降至 26 秒。" }
        ]
      }
    ];

    const ANCHOR_PROFILES = {
      fashion: {
        accountId: "fashion",
        anchorId: "A-1024",
        name: "林小祺",
        avatar: "林",
        gender: "女",
        age: 26,
        experience: "3 年",
        totalSessions: 428,
        category: "女装 / 秋冬",
        avgDwell: 42.6,
        tags: ["亲和型", "专业讲解", "快节奏促单"],
        style: [
          { label: "亲和力", value: 88 },
          { label: "节奏感", value: 82 },
          { label: "专业度", value: 76 },
          { label: "互动性", value: 71 },
          { label: "促单力", value: 84 }
        ],
        state: [
          { label: "语速", value: "5.2 字/秒", tone: "", note: "偏快但清晰" },
          { label: "能量状态", value: "饱满", tone: "good", note: "近 3 场稳定" },
          { label: "情绪稳定", value: "87", tone: "good", note: "波动较小" },
          { label: "疲劳指数", value: "低", tone: "good", note: "适合保持当前排班" }
        ],
        learnedSessions: 12,
        learnedHours: 36.4,
        confidence: 86,
        bestTime: "19:30–22:30",
        bestTimeReason: "历史高转化场次集中在晚场，20:30 后返场节奏更稳定。",
        scriptMatch: ["专业讲解 + 场景演示", "价格对比 + 限时福利", "高互动问答"],
        insight: "主播属于亲和型专业讲解风格，语速中等偏快，擅长用场景演示承接流量。历史出单高峰通常出现在开播 25-40 分钟和返场后 10 分钟。",
        orderRhythm: [32, 48, 55, 62, 58, 74, 82, 88, 76, 91, 84, 72],
        peakWindows: ["开播 25–40 分钟", "返场后 10 分钟"],
        faceConfidence: 96,
        reviewLinkNote: "本场开播 25-40 分钟的成交节奏高于历史均值，与主播擅长的场景演示节奏一致；后段价格异议阶段低于历史水平。"
      },
      home: {
        accountId: "home",
        anchorId: "A-2081",
        name: "周然",
        avatar: "周",
        gender: "女",
        age: 31,
        experience: "4 年",
        totalSessions: 612,
        category: "家居 / 内衣",
        avgDwell: 38.4,
        tags: ["场景种草型", "耐心讲解", "稳定型"],
        style: [
          { label: "亲和力", value: 91 },
          { label: "节奏感", value: 70 },
          { label: "专业度", value: 84 },
          { label: "互动性", value: 68 },
          { label: "促单力", value: 73 }
        ],
        state: [
          { label: "语速", value: "4.6 字/秒", tone: "", note: "舒缓清楚" },
          { label: "能量状态", value: "稳定", tone: "good", note: "适合长时段" },
          { label: "情绪稳定", value: "91", tone: "good", note: "情绪波动低" },
          { label: "疲劳指数", value: "中", tone: "warn", note: "连续两场后需休息" }
        ],
        learnedSessions: 18,
        learnedHours: 54.2,
        confidence: 91,
        bestTime: "20:00–22:30",
        bestTimeReason: "耐心讲解在晚间家庭场景下更容易形成停留，20:30 后组合装成交更稳定。",
        scriptMatch: ["场景种草 + 尺码答疑", "组合装 + 福利返场"],
        insight: "主播属于场景种草型，语速舒缓、专业度高，擅长用生活场景和细节演示建立信任。历史出单高峰集中在开播 30-50 分钟和福利款返场阶段。",
        orderRhythm: [28, 38, 52, 61, 72, 78, 74, 85, 81, 88, 76, 68],
        peakWindows: ["开播 30–50 分钟", "福利款返场"],
        faceConfidence: 94,
        reviewLinkNote: "本场与历史出单节奏基本一致，场景演示段落仍是最稳定的成交区间；尺码咨询阶段的成交效率略低于历史水平。"
      },
      select: {
        accountId: "select",
        anchorId: "A-3157",
        name: "陈一诺",
        avatar: "陈",
        gender: "女",
        age: 24,
        experience: "1.5 年",
        totalSessions: 186,
        category: "配饰 / 礼赠",
        avgDwell: 31.8,
        tags: ["快节奏型", "多色展示", "礼赠场景"],
        style: [
          { label: "亲和力", value: 78 },
          { label: "节奏感", value: 88 },
          { label: "专业度", value: 68 },
          { label: "互动性", value: 75 },
          { label: "促单力", value: 80 }
        ],
        state: [
          { label: "语速", value: "5.6 字/秒", tone: "", note: "快节奏" },
          { label: "能量状态", value: "高", tone: "good", note: "适合短时爆发" },
          { label: "情绪稳定", value: "82", tone: "", note: "后段易波动" },
          { label: "疲劳指数", value: "中", tone: "warn", note: "建议控制连续场次" }
        ],
        learnedSessions: 7,
        learnedHours: 18.6,
        confidence: 74,
        bestTime: "14:00–17:00",
        bestTimeReason: "快节奏多色展示更适合下午短时段，历史转化高峰集中在开播前 40 分钟。",
        scriptMatch: ["多色展示 + 快速过款", "节日礼赠 + 价格锚点"],
        insight: "主播属于快节奏多色展示型，适合短时爆发和礼赠场景，但后段容易出现节奏下滑。建议拆成 40-60 分钟短场，并固定价格对比与返场动作。",
        orderRhythm: [42, 58, 72, 86, 78, 64, 56, 48, 44, 39, 35, 30],
        peakWindows: ["开播 0–30 分钟", "多色展示段"],
        faceConfidence: 89,
        reviewLinkNote: "本场前 30 分钟与历史出单高峰一致，但后段节奏和成交下滑明显，建议缩短单场时长并增加一次返场。"
      }
    };

    const ANCHOR_UPLOADS = {
      fashion: [
        { id: "sample-f1", name: "2026-10-10_晚场录屏.mp4", size: 195 * 1024 * 1024, status: "done", progress: 100, tag: "优势：爆款返场节奏", note: "已加入风格模型" },
        { id: "sample-f2", name: "2026-10-08_午场录屏.mov", size: 149 * 1024 * 1024, status: "done", progress: 100, tag: "优势：面料演示", note: "已加入风格模型" }
      ],
      home: [
        { id: "sample-h1", name: "2026-10-12_晚场录屏.mp4", size: 212 * 1024 * 1024, status: "done", progress: 100, tag: "优势：场景种草", note: "已加入风格模型" }
      ],
      select: [
        { id: "sample-s1", name: "2026-10-11_下午场录屏.mp4", size: 126 * 1024 * 1024, status: "done", progress: 100, tag: "优势：多色展示", note: "已加入风格模型" }
      ]
    };

    const DIAG_LIVE = {
      fashion: {
        live: true,
        anchorName: "林小祺",
        anchorBadge: "良好",
        anchorTone: "good",
        anchorMetrics: [
          { label: "语速", value: "5.2 字/秒", note: "偏快但清晰" },
          { label: "能量", value: "82", note: "状态稳定" },
          { label: "情绪", value: "87", note: "波动较小" },
          { label: "疲劳", value: "低", note: "适合当前时段" }
        ],
        scriptIssues: [
          { time: "20:14:22", phrase: "最便宜", type: "绝对化用语", level: "bad", note: "建议改为“当前活动价更低”。" },
          { time: "20:16:05", phrase: "保证", type: "承诺性用语", level: "bad", note: "承诺效果需谨慎，建议补充适用条件。" },
          { time: "20:18:40", phrase: "连续 18 秒无互动", type: "节奏提醒", level: "warn", note: "插入提问或福利提醒。" }
        ],
        user: { watchRate: 18.6, productClicks: 1284, productClickRate: 8.4, dwell: 42.6, online: 12840, comments: 326 },
        goods: { product: "秋冬冲锋衣", stock: 328, conversion: 3.18, scene: "画面清晰 · 灯光正常", interaction: "互动平稳" },
        base: { anchor: 78, user: 72, goods: 74 },
        riskPhrases: ["最便宜", "保证", "全网最低", "百分百"]
      },
      home: {
        live: true,
        anchorName: "周然",
        anchorBadge: "稳定",
        anchorTone: "good",
        anchorMetrics: [
          { label: "语速", value: "4.6 字/秒", note: "舒缓清楚" },
          { label: "能量", value: "76", note: "长时段稳定" },
          { label: "情绪", value: "91", note: "波动低" },
          { label: "疲劳", value: "中", note: "连续两场需休息" }
        ],
        scriptIssues: [
          { time: "20:08:12", phrase: "全网最低", type: "绝对化用语", level: "bad", note: "建议改为“同价位更有优势”。" },
          { time: "20:17:36", phrase: "百分百", type: "承诺性用语", level: "warn", note: "避免绝对化承诺。" }
        ],
        user: { watchRate: 16.2, productClicks: 642, productClickRate: 7.1, dwell: 38.4, online: 6420, comments: 188 },
        goods: { product: "加厚家居服", stock: 186, conversion: 2.94, scene: "卧室场景 · 光线柔和", interaction: "咨询较多" },
        base: { anchor: 74, user: 68, goods: 71 },
        riskPhrases: ["全网最低", "百分百", "绝对", "保证"]
      },
      select: {
        live: false,
        anchorName: "陈一诺",
        anchorBadge: "待开播",
        anchorTone: "warn",
        anchorMetrics: [
          { label: "语速", value: "5.6 字/秒", note: "快节奏" },
          { label: "能量", value: "85", note: "适合短时爆发" },
          { label: "情绪", value: "82", note: "后段易波动" },
          { label: "疲劳", value: "中", note: "建议控制场次" }
        ],
        scriptIssues: [
          { time: "15:12:08", phrase: "绝对", type: "绝对化用语", level: "bad", note: "上一场遗留风险，待复核。" },
          { time: "15:16:40", phrase: "停留时长下滑", type: "节奏提醒", level: "warn", note: "后段讲解节奏偏慢。" }
        ],
        user: { watchRate: 14.8, productClicks: 318, productClickRate: 6.6, dwell: 31.8, online: 2260, comments: 96 },
        goods: { product: "羊毛围巾", stock: 92, conversion: 2.72, scene: "陈列完整 · 背景偏暗", interaction: "互动偏弱" },
        base: { anchor: 66, user: 60, goods: 58 },
        riskPhrases: ["绝对", "最便宜", "保证", "百分百"]
      }
    };

    const BANNED_CATEGORIES = [
      { id: "all", label: "全部分类" },
      { id: "absolute", label: "绝对化用语" },
      { id: "promise", label: "承诺性用语" },
      { id: "efficacy", label: "功效宣称" },
      { id: "price", label: "价格诱导" },
      { id: "platform", label: "平台禁用" },
      { id: "pending", label: "待分类" }
    ];

    const BANNED_LIBRARY_META = {
      total: 1286,
      weeklyNew: 38,
      highRisk: 74,
      updated: "10/16 18:20"
    };

    const BANNED_WORDS = [
      { id: "bw-01", word: "最便宜", categoryId: "absolute", level: "high", note: "价格比较无依据，容易构成绝对化宣传。", replacement: "改为“当前活动价更低”", source: "千川规则", updated: "10/16", status: "生效", hits: 42 },
      { id: "bw-02", word: "全网最低", categoryId: "absolute", level: "high", note: "无法验证的全网比较。", replacement: "改为“同价位更有优势”", source: "千川规则", updated: "10/16", status: "生效", hits: 37 },
      { id: "bw-03", word: "绝对", categoryId: "absolute", level: "high", note: "绝对化承诺，缺少适用条件。", replacement: "改为“在当前使用条件下”", source: "团队复盘", updated: "10/15", status: "生效", hits: 29 },
      { id: "bw-04", word: "第一", categoryId: "absolute", level: "high", note: "排名类表述需提供权威依据。", replacement: "删除排名，改为具体卖点", source: "千川规则", updated: "10/15", status: "生效", hits: 18 },
      { id: "bw-05", word: "国家级", categoryId: "absolute", level: "high", note: "资质类绝对化用语。", replacement: "改为“符合相关标准”", source: "千川规则", updated: "10/14", status: "生效", hits: 7 },
      { id: "bw-06", word: "保证", categoryId: "promise", level: "high", note: "效果承诺需谨慎，容易引发售后争议。", replacement: "改为“多数用户反馈”并补充条件", source: "团队复盘", updated: "10/16", status: "生效", hits: 34 },
      { id: "bw-07", word: "百分百", categoryId: "promise", level: "high", note: "绝对化承诺，无法保证个体结果。", replacement: "改为“高概率”或删除", source: "千川规则", updated: "10/16", status: "生效", hits: 26 },
      { id: "bw-08", word: "永久", categoryId: "promise", level: "high", note: "永久有效类承诺不可验证。", replacement: "改为明确质保周期", source: "团队复盘", updated: "10/13", status: "待复核", hits: 9 },
      { id: "bw-09", word: "无效退款", categoryId: "promise", level: "mid", note: "需同时说明退款条件与流程。", replacement: "改为“按平台规则支持售后”", source: "团队复盘", updated: "10/12", status: "生效", hits: 12 },
      { id: "bw-10", word: "治疗", categoryId: "efficacy", level: "high", note: "普通商品不得宣称医疗作用。", replacement: "删除医疗功效描述", source: "平台规则", updated: "10/16", status: "生效", hits: 15 },
      { id: "bw-11", word: "消炎", categoryId: "efficacy", level: "high", note: "医疗功效宣称，普通服饰不适用。", replacement: "改为“亲肤透气”", source: "平台规则", updated: "10/16", status: "生效", hits: 8 },
      { id: "bw-12", word: "抗癌", categoryId: "efficacy", level: "high", note: "严重医疗功效宣称。", replacement: "删除相关表述", source: "平台规则", updated: "10/15", status: "生效", hits: 3 },
      { id: "bw-13", word: "降血压", categoryId: "efficacy", level: "high", note: "医疗功效宣称，需严格拦截。", replacement: "删除相关表述", source: "平台规则", updated: "10/15", status: "生效", hits: 4 },
      { id: "bw-14", word: "包治百病", categoryId: "efficacy", level: "high", note: "典型夸大功效用语。", replacement: "删除相关表述", source: "平台规则", updated: "10/14", status: "生效", hits: 2 },
      { id: "bw-15", word: "原价", categoryId: "price", level: "mid", note: "需能证明原价真实存在及持续时间。", replacement: "改为“日常价”并标注周期", source: "千川规则", updated: "10/13", status: "生效", hits: 21 },
      { id: "bw-16", word: "最后一天", categoryId: "price", level: "mid", note: "限时表述需与实际活动一致。", replacement: "改为具体活动截止时间", source: "团队复盘", updated: "10/16", status: "生效", hits: 33 },
      { id: "bw-17", word: "亏本清仓", categoryId: "price", level: "mid", note: "价格诱导，需谨慎使用。", replacement: "改为“活动专场价”", source: "团队复盘", updated: "10/11", status: "待复核", hits: 14 },
      { id: "bw-18", word: "点击领红包", categoryId: "platform", level: "mid", note: "站外引导或虚假利益诱导。", replacement: "改为平台内合规优惠说明", source: "平台规则", updated: "10/16", status: "生效", hits: 11 },
      { id: "bw-19", word: "私信加微信", categoryId: "platform", level: "high", note: "站外导流，平台明确限制。", replacement: "引导至平台内客服或橱窗", source: "平台规则", updated: "10/16", status: "生效", hits: 6 },
      { id: "bw-20", word: "站外下单", categoryId: "platform", level: "high", note: "引导站外交易。", replacement: "引导至直播间购物车", source: "平台规则", updated: "10/15", status: "生效", hits: 3 },
      { id: "bw-21", word: "秒杀", categoryId: "platform", level: "mid", note: "需与平台活动类型一致，避免误导。", replacement: "改为“限时活动”", source: "团队复盘", updated: "10/10", status: "待复核", hits: 17 }
    ];

    const BANNED_VERSIONS = [
      { version: "V2.8", date: "10/16", note: "新增高频词 38 条", count: "+38" },
      { version: "V2.7", date: "10/09", note: "同步平台规则 24 条", count: "+24" },
      { version: "V2.6", date: "09/30", note: "团队复盘补充 61 条", count: "+61" }
    ];

    const UPLOAD_CHANNELS = [
      { title: "本地上传 TXT / CSV", status: "可用", tone: "good", desc: "一行一个词条；CSV 支持“词条,分类,风险等级,替换建议”。", action: "local" },
      { title: "团队共享表格", status: "待接入", tone: "warn", desc: "飞书 / 企微表格增量同步，按更新时间拉取新增词条。", action: null },
      { title: "千川后台词库", status: "待接入", tone: "warn", desc: "通过千川 API 同步平台词库，需申请词库读取权限。", action: null },
      { title: "开放 API 推送", status: "待接入", tone: "muted", desc: "提供 POST 接口，供内部风控或第三方词库持续推送。", action: null }
    ];

    const QUALITY_META = {
      fashion: {
        anchorId: "A-1024",
        name: "林小祺",
        avatar: "林",
        session: "10/16 晚场",
        extracted: 8,
        highConversion: 5,
        highDwell: 4,
        confidence: 86,
        orderPeak: "开播 25–40 分钟"
      },
      home: {
        anchorId: "A-2081",
        name: "周然",
        avatar: "周",
        session: "10/16 晚场",
        extracted: 7,
        highConversion: 4,
        highDwell: 5,
        confidence: 91,
        orderPeak: "开播 30–50 分钟"
      },
      select: {
        anchorId: "A-3157",
        name: "陈一诺",
        avatar: "陈",
        session: "10/16 下午场",
        extracted: 6,
        highConversion: 4,
        highDwell: 3,
        confidence: 74,
        orderPeak: "开播前 30 分钟"
      }
    };

    const QUALITY_SCRIPTS = [
      { id: "fashion-1", accountId: "fashion", scene: "产品演示", quote: "这个面料我给你近一点看，袖口这里是有弹力的，抬手不会勒，通勤骑车都方便。", conversion: 5.8, dwell: 51.2, uses: 12, lift: 38, date: "10/16", timecode: "20:32" },
      { id: "fashion-2", accountId: "fashion", scene: "上身对比", quote: "先别急着拍，我把三个颜色都上身给你看，黄皮选这个燕麦色最稳。", conversion: 5.2, dwell: 48.6, uses: 9, lift: 31, date: "10/16", timecode: "20:18" },
      { id: "fashion-3", accountId: "fashion", scene: "价格锚点", quote: "今天这个价格是直播间专享，外面同款你去比，贵出来的部分我来补。", conversion: 6.1, dwell: 44.1, uses: 14, lift: 42, date: "10/15", timecode: "21:06" },
      { id: "fashion-4", accountId: "fashion", scene: "限时促单", quote: "最后 3 分钟，刚才没抢到的姐妹扣个 1，我让运营再加一波库存。", conversion: 7.4, dwell: 39.8, uses: 7, lift: 57, date: "10/16", timecode: "21:36" },
      { id: "home-1", accountId: "home", scene: "材质实验", quote: "你摸一下这个绒，它不是那种一洗就塌的，我拿吹风机给你吹一下看回弹。", conversion: 4.9, dwell: 56.3, uses: 11, lift: 34, date: "10/16", timecode: "20:42" },
      { id: "home-2", accountId: "home", scene: "尺码答疑", quote: "小个子姐妹看这里，裤脚我往上折两公分，比例马上就出来了。", conversion: 4.6, dwell: 52.7, uses: 8, lift: 26, date: "10/16", timecode: "21:12" },
      { id: "home-3", accountId: "home", scene: "组合装", quote: "这个四件套我建议直接入两套，一套换洗一套铺，算下来比单买省 80。", conversion: 5.3, dwell: 47.9, uses: 6, lift: 29, date: "10/15", timecode: "20:58" },
      { id: "home-4", accountId: "home", scene: "场景种草", quote: "卧室灯我关一半，你们看这个颜色在晚上是不是更柔和。", conversion: 4.8, dwell: 58.1, uses: 10, lift: 32, date: "10/16", timecode: "20:26" },
      { id: "select-1", accountId: "select", scene: "多色展示", quote: "这条围巾我不系复杂结，就绕一圈，通勤和约会都能用。", conversion: 5.7, dwell: 41.2, uses: 13, lift: 35, date: "10/16", timecode: "14:48" },
      { id: "select-2", accountId: "select", scene: "礼赠场景", quote: "送妈妈选这个驼色，送闺蜜选雾蓝，我把礼盒也给你们搭好。", conversion: 6.3, dwell: 45.8, uses: 9, lift: 46, date: "10/16", timecode: "15:12" },
      { id: "select-3", accountId: "select", scene: "价格对比", quote: "同价位你去看成分标，这条含羊毛量更高，手感完全不一样。", conversion: 4.4, dwell: 38.7, uses: 6, lift: 19, date: "10/15", timecode: "15:36" },
      { id: "select-4", accountId: "select", scene: "限时促单", quote: "最后 20 条，拍下备注颜色，我优先给你发。", conversion: 6.8, dwell: 36.4, uses: 5, lift: 41, date: "10/16", timecode: "16:02" }
    ];

    const LOW_SCRIPTS = [
      { id: "low-01", accountId: "fashion", scene: "产品介绍", quote: "这个款真的闭眼入，谁穿都好看。", occurrences: 14, dwell: 21.4, conversion: 1.8, baseline: 3.4, lastSeen: "10/16 20:54", suggestion: "替换为具体版型、面料或人群适配描述", status: "待优化" },
      { id: "low-02", accountId: "fashion", scene: "互动引导", quote: "家人们点点赞，马上给你们上福利。", occurrences: 11, dwell: 19.6, conversion: 2.0, baseline: 3.3, lastSeen: "10/16 21:18", suggestion: "把福利内容和时间点说具体，减少空泛互动", status: "待优化" },
      { id: "low-03", accountId: "fashion", scene: "重复讲解", quote: "我再讲一遍，刚才没听清的姐妹听好。", occurrences: 9, dwell: 26.8, conversion: 1.7, baseline: 3.2, lastSeen: "10/15 20:36", suggestion: "删减重复段，改用提问确认用户需求", status: "待优化" },
      { id: "low-04", accountId: "fashion", scene: "价格表达", quote: "这个价格已经是最低了，别的地方买不到。", occurrences: 8, dwell: 24.2, conversion: 2.1, baseline: 3.5, lastSeen: "10/15 21:02", suggestion: "删除绝对化价格表达，改为同价位对比", status: "已优化" },
      { id: "low-05", accountId: "home", scene: "材质说明", quote: "这个材质你们收到就知道了，反正很好。", occurrences: 12, dwell: 23.7, conversion: 1.9, baseline: 3.1, lastSeen: "10/16 21:04", suggestion: "增加克重、回弹或洗后对比的实证演示", status: "待优化" },
      { id: "low-06", accountId: "home", scene: "尺码答疑", quote: "尺码你们按平时穿的拍就行。", occurrences: 10, dwell: 27.5, conversion: 2.2, baseline: 3.0, lastSeen: "10/16 20:48", suggestion: "前置身高体重对照表，减少模糊回答", status: "待优化" },
      { id: "low-07", accountId: "home", scene: "场景描述", quote: "这个放家里肯定好看，怎么搭都行。", occurrences: 7, dwell: 22.1, conversion: 1.8, baseline: 2.9, lastSeen: "10/15 20:22", suggestion: "改为具体卧室/客厅场景对比", status: "已优化" },
      { id: "low-08", accountId: "select", scene: "互动引导", quote: "喜欢的直接拍，不喜欢可以退。", occurrences: 13, dwell: 18.9, conversion: 1.6, baseline: 2.8, lastSeen: "10/16 15:48", suggestion: "补充颜色选择、成分和礼赠理由", status: "待优化" },
      { id: "low-09", accountId: "select", scene: "价格表达", quote: "今天不买明天就恢复原价了。", occurrences: 9, dwell: 20.4, conversion: 1.9, baseline: 2.7, lastSeen: "10/16 15:56", suggestion: "明确活动截止时间，避免模糊价格催促", status: "待优化" },
      { id: "low-10", accountId: "select", scene: "多色展示", quote: "颜色都在下面，你们自己看。", occurrences: 8, dwell: 17.8, conversion: 1.5, baseline: 2.6, lastSeen: "10/15 16:08", suggestion: "逐一上身展示高转化色，并说明适配肤色", status: "待优化" },
      { id: "low-11", accountId: "select", scene: "礼赠场景", quote: "送人肯定有面子，包装也好看。", occurrences: 6, dwell: 19.2, conversion: 1.7, baseline: 2.6, lastSeen: "10/15 15:42", suggestion: "补充收礼对象与搭配建议，加入礼盒实拍", status: "已优化" },
      { id: "low-12", accountId: "fashion", scene: "开场承接", quote: "刚进来的姐妹先点个关注，等下慢慢看。", occurrences: 7, dwell: 18.5, conversion: 1.4, baseline: 3.0, lastSeen: "10/14 20:06", suggestion: "开场 30 秒先给当前爆款与福利信息", status: "待优化" }
    ];

    const SCRIPT_LIVE = {
      fashion: {
        live: true,
        comments: ["燕麦色还有 M 码吗？", "刚进来，多少钱？", "这个袖口会起球吗？", "已拍，坐等发货", "身高 165 选哪个码？", "这个颜色显白吗？", "最后那件还有吗？", "比昨天便宜多少？"],
        sentences: [
          { text: "这个面料我给你近一点看，袖口是有弹力的，抬手不会勒。", tag: "高停留", commentDelta: 18, dwellDelta: 6.8, orderDelta: 3, score: 88 },
          { text: "先别急着拍，我把三个颜色都上身给你看，黄皮选燕麦色最稳。", tag: "高转化", commentDelta: 12, dwellDelta: 4.2, orderDelta: 9, score: 92 },
          { text: "这个价格你们去外面比，同款不会比今天低。", tag: "风险", commentDelta: 22, dwellDelta: -1.8, orderDelta: 1, score: 48 },
          { text: "最后 3 分钟，没抢到的扣 1，我让运营再加一波库存。", tag: "高转化", commentDelta: 31, dwellDelta: 3.4, orderDelta: 14, score: 96 },
          { text: "刚进来的姐妹，我先用 30 秒讲清楚这件衣服怎么选。", tag: "高停留", commentDelta: 15, dwellDelta: 8.2, orderDelta: 2, score: 87 },
          { text: "我再讲一遍，刚才没听清的听好。", tag: "低效", commentDelta: 4, dwellDelta: -3.6, orderDelta: -1, score: 35 },
          { text: "这个款真的闭眼入，谁穿都好看。", tag: "低效", commentDelta: 6, dwellDelta: -2.4, orderDelta: 0, score: 41 },
          { text: "你们摸不到面料，我把镜头拉近，看这个绒的密度。", tag: "高停留", commentDelta: 19, dwellDelta: 5.6, orderDelta: 4, score: 85 },
          { text: "库存还有 328 件，卖完这场就恢复原价。", tag: "高转化", commentDelta: 24, dwellDelta: 1.9, orderDelta: 11, score: 90 }
        ]
      },
      home: {
        live: true,
        comments: ["四件套是什么材质？", "小个子能穿吗？", "这个颜色耐脏吗？", "已经下单两套", "有没有 1.8 米床的？", "洗了会缩水吗？", "组合装还能加吗？", "卧室灯是什么色温？"],
        sentences: [
          { text: "你摸一下这个绒，它不是那种一洗就塌的，我拿吹风机给你吹一下看回弹。", tag: "高停留", commentDelta: 17, dwellDelta: 9.4, orderDelta: 3, score: 91 },
          { text: "小个子姐妹看这里，裤脚我往上折两公分，比例马上就出来了。", tag: "高转化", commentDelta: 14, dwellDelta: 5.1, orderDelta: 8, score: 89 },
          { text: "这个四件套我建议直接入两套，一套换洗一套铺，算下来比单买省 80。", tag: "高转化", commentDelta: 21, dwellDelta: 2.8, orderDelta: 12, score: 93 },
          { text: "尺码你们按平时穿的拍就行。", tag: "低效", commentDelta: 3, dwellDelta: -2.7, orderDelta: 0, score: 38 },
          { text: "卧室灯我关一半，你们看这个颜色在晚上是不是更柔和。", tag: "高停留", commentDelta: 13, dwellDelta: 7.6, orderDelta: 4, score: 87 },
          { text: "这个材质你们收到就知道了，反正很好。", tag: "低效", commentDelta: 5, dwellDelta: -3.1, orderDelta: -1, score: 34 },
          { text: "组合装今天只上 50 套，拍下我优先给你发同色系。", tag: "高转化", commentDelta: 19, dwellDelta: 1.2, orderDelta: 10, score: 88 },
          { text: "刚进来的姐妹，我把床品尺寸和适配床型再讲一遍。", tag: "高停留", commentDelta: 11, dwellDelta: 4.8, orderDelta: 2, score: 80 }
        ]
      },
      select: {
        live: false,
        comments: ["驼色还有吗？", "礼盒是免费的吗？", "这条扎脖子吗？", "送妈妈选哪个色？", "能开发票吗？", "最后 20 条真的吗？", "雾蓝什么时候补货？", "成分标在哪里看？"],
        sentences: [
          { text: "这条围巾我不系复杂结，就绕一圈，通勤和约会都能用。", tag: "高转化", commentDelta: 16, dwellDelta: 3.6, orderDelta: 7, score: 86 },
          { text: "送妈妈选这个驼色，送闺蜜选雾蓝，我把礼盒也给你们搭好。", tag: "高转化", commentDelta: 23, dwellDelta: 2.9, orderDelta: 11, score: 94 },
          { text: "同价位你去看成分标，这条含羊毛量更高，手感完全不一样。", tag: "高停留", commentDelta: 9, dwellDelta: 6.2, orderDelta: 4, score: 83 },
          { text: "喜欢的直接拍，不喜欢可以退。", tag: "低效", commentDelta: 4, dwellDelta: -2.2, orderDelta: 0, score: 39 },
          { text: "最后 20 条，拍下备注颜色，我优先给你发。", tag: "高转化", commentDelta: 18, dwellDelta: 1.1, orderDelta: 9, score: 88 },
          { text: "颜色都在下面，你们自己看。", tag: "低效", commentDelta: 2, dwellDelta: -3.8, orderDelta: -1, score: 30 },
          { text: "我把礼盒打开给你们看，丝带和卡片都是配好的。", tag: "高停留", commentDelta: 12, dwellDelta: 5.4, orderDelta: 3, score: 82 }
        ]
      }
    };

    const CAMPAIGN_DATA = {
      fashion: {
        summary: { spend: 28600, spendRate: 3860, roi: 4.31, orders: 612, ordersRate: 82, paidShare: 60, online: 12840, cvr: 3.18 },
        channels: [
          { name: "付费推荐", color: "#0b7a58", share: 42, spend: 1620, roi: 4.1, trend: 8.4 },
          { name: "搜索", color: "#2b6f94", share: 18, spend: 694, roi: 4.8, trend: 3.1 },
          { name: "自然推荐", color: "#c9723c", share: 25, spend: 0, roi: 5.6, trend: -2.6 },
          { name: "关注", color: "#8e6a2f", share: 9, spend: 0, roi: 6.2, trend: 1.8 },
          { name: "其他", color: "#a8b3ab", share: 6, spend: 231, roi: 3.1, trend: -4.2 }
        ],
        persona: {
          gender: [["女", 86], ["男", 14]],
          age: [["25-34", 46], ["35-44", 27], ["18-24", 18], ["45+", 9]],
          region: "华东 32% · 华南 24% · 华北 18%",
          tags: ["秋冬外套", "通勤穿搭", "价格敏感", "高点击低转化", "晚间活跃"]
        },
        signals: [
          { label: "主播状态", value: "良好 82", tone: "good", note: "语速 5.2 字/秒 · 情绪稳定" },
          { label: "日时段", value: "晚场黄金段", tone: "good", note: "20:00–22:30 历史转化最高" },
          { label: "渠道结构", value: "付费占 60%", tone: "warn", note: "付费推荐偏泛，自然流量回落" },
          { label: "货场承接", value: "库存 328 件", tone: "good", note: "点击率 8.4% · 转化 3.18%" }
        ],
        decisions: {
          morning: { action: "小额测试放量", percent: 5, confidence: 72, reason: "早场流量成本较低，但主播能量与成交承接尚未完全起量。先用小额预算测试人群，不一次性放大。", guardrail: "30 分钟内 ROI 低于 3.2 或转化率低于 2.4% 时停止。", expected: ["消耗 +5%", "ROI ±0.15", "订单 +3%–5%"] },
          noon: { action: "控成本追投", percent: 6, confidence: 78, reason: "午场自然流量占比回升，搜索渠道 ROI 高于付费推荐。保持成本上限，优先给搜索与高转化人群加预算。", guardrail: "ROI 低于 3.4 或付费推荐占比超过 65% 时停止。", expected: ["消耗 +6%", "ROI +0.05", "订单 +4%–7%"] },
          evening: { action: "控成本追投", percent: 8, confidence: 84, reason: "主播状态稳定、晚场成交效率上行，但付费推荐占比偏高且自然流量下滑。建议小步追投，守住成本上限，避免放量后流量变泛。", guardrail: "ROI 低于 3.6 或转化率低于 2.8% 时立即停止。", expected: ["消耗 +8%", "ROI 持平 ±0.1", "订单 +6%–9%"] }
        },
        anomalies: [
          { time: "20:15–20:25", severity: "高", metric: "付费推荐流量突增 42%，ROI 4.2 → 2.9", cause: "放量后人群变泛，新客占比上升 18%", suggestion: "控成本追投 -10%，收紧高转化人群包" },
          { time: "20:40–20:50", severity: "中", metric: "自然流量骤降 31%，在线人数 -12%", cause: "直播间互动下降，推荐流量回落", suggestion: "插入福利款返场，增加一次互动提问" },
          { time: "20:55–21:05", severity: "中", metric: "搜索流量成本上升 22%", cause: "同类目竞价加剧，搜索计划出价偏高", suggestion: "搜索计划降价 5%，保留高转化词" }
        ],
        series: [
          { label: "20:00", spend: 18, roi: 4.6, online: 11.2 },
          { label: "20:05", spend: 21, roi: 4.5, online: 11.8 },
          { label: "20:10", spend: 27, roi: 4.1, online: 12.4 },
          { label: "20:15", spend: 35, roi: 2.9, online: 13.1, flagged: true },
          { label: "20:20", spend: 32, roi: 3.1, online: 13.4, flagged: true },
          { label: "20:25", spend: 28, roi: 3.4, online: 12.9 },
          { label: "20:30", spend: 22, roi: 4.3, online: 12.2 },
          { label: "20:35", spend: 20, roi: 4.5, online: 11.9 },
          { label: "20:40", spend: 19, roi: 4.4, online: 10.4 },
          { label: "20:45", spend: 18, roi: 4.2, online: 9.8, flagged: true },
          { label: "20:50", spend: 21, roi: 4.0, online: 10.1 },
          { label: "20:55", spend: 26, roi: 3.7, online: 10.8, flagged: true },
          { label: "21:00", spend: 28, roi: 3.5, online: 11.4 }
        ],
        docs: [
          { id: "doc-f1", name: "千川放量策略复盘_2026Q3.pdf", type: "PDF", size: "2.4 MB", status: "已学习", rules: 6, date: "10/12" },
          { id: "doc-f2", name: "晚场直播投放节奏 SOP.docx", type: "DOCX", size: "860 KB", status: "已学习", rules: 4, date: "10/14" },
          { id: "doc-f3", name: "秋冬服饰人群包测试.xlsx", type: "XLSX", size: "1.1 MB", status: "已学习", rules: 3, date: "10/15" }
        ],
        rules: [
          "晚场 20:00–22:00，ROI ≥ 4.0 才进入放量。",
          "单次放量不超过 15%，观察 30 分钟后再决定是否追加。",
          "控成本追投优先于一键放量，先守住成本上限。",
          "搜索流量 ROI < 3.5 时，降低出价 5% 并保留高转化词。"
        ]
      },
      home: {
        summary: { spend: 14200, spendRate: 1860, roi: 4.18, orders: 286, ordersRate: 38, paidShare: 54, online: 6420, cvr: 2.94 },
        channels: [
          { name: "付费推荐", color: "#0b7a58", share: 36, spend: 864, roi: 3.9, trend: 4.1 },
          { name: "搜索", color: "#2b6f94", share: 18, spend: 332, roi: 4.6, trend: 2.4 },
          { name: "自然推荐", color: "#c9723c", share: 30, spend: 0, roi: 5.1, trend: -1.2 },
          { name: "关注", color: "#8e6a2f", share: 10, spend: 0, roi: 5.8, trend: 1.1 },
          { name: "其他", color: "#a8b3ab", share: 6, spend: 144, roi: 2.8, trend: -3.5 }
        ],
        persona: {
          gender: [["女", 78], ["男", 22]],
          age: [["25-34", 38], ["35-44", 31], ["45+", 19], ["18-24", 12]],
          region: "华东 28% · 华中 23% · 华南 21%",
          tags: ["家居焕新", "亲子家庭", "注重材质", "长停留", "组合装偏好"]
        },
        signals: [
          { label: "主播状态", value: "稳定 76", tone: "good", note: "语速 4.6 字/秒 · 长时段稳定" },
          { label: "日时段", value: "晚场稳定段", tone: "good", note: "20:30 后组合装成交更稳" },
          { label: "渠道结构", value: "自然占 40%", tone: "good", note: "自然推荐 ROI 高于付费" },
          { label: "货场承接", value: "库存 186 件", tone: "warn", note: "尺码咨询较多" }
        ],
        decisions: {
          morning: { action: "小额测试放量", percent: 4, confidence: 70, reason: "早场家居人群停留较长但成交密度低，先测试材质演示段落，不放大付费预算。", guardrail: "ROI 低于 3.0 或停留低于 30 秒时停止。", expected: ["消耗 +4%", "ROI ±0.12", "订单 +2%–4%"] },
          noon: { action: "控成本追投", percent: 5, confidence: 76, reason: "午场自然流量稳定，组合装点击率较高。保持成本上限，给自然流量承接好的计划小幅加预算。", guardrail: "ROI 低于 3.3 或付费占比超过 60% 时停止。", expected: ["消耗 +5%", "ROI +0.04", "订单 +3%–6%"] },
          evening: { action: "控成本追投", percent: 6, confidence: 80, reason: "主播状态稳定，自然推荐占比高，但库存和尺码咨询是承接短板。建议小幅追投，同时前置尺码讲解。", guardrail: "ROI 低于 3.4 或尺码咨询继续上升时停止。", expected: ["消耗 +6%", "ROI +0.03", "订单 +4%–7%"] }
        },
        anomalies: [
          { time: "20:10–20:20", severity: "中", metric: "自然流量下降 18%，在线人数 -8%", cause: "场景演示节奏变慢，互动减少", suggestion: "插入材质实验，提升停留与互动" },
          { time: "20:35–20:45", severity: "高", metric: "尺码咨询集中，转化率降至 2.3%", cause: "尺码表未前置，评论区重复提问", suggestion: "固定尺码表口播，并置顶尺码卡片" },
          { time: "21:00–21:10", severity: "中", metric: "付费推荐 ROI 降至 3.2", cause: "组合装人群变泛，点击成本上升", suggestion: "控成本追投 -8%，收紧组合装人群" }
        ],
        series: [
          { label: "19:45", spend: 12, roi: 4.4, online: 5.1 },
          { label: "19:50", spend: 14, roi: 4.3, online: 5.4 },
          { label: "19:55", spend: 17, roi: 4.1, online: 5.8 },
          { label: "20:00", spend: 21, roi: 3.8, online: 6.0 },
          { label: "20:05", spend: 18, roi: 3.6, online: 5.7 },
          { label: "20:10", spend: 16, roi: 3.4, online: 5.2, flagged: true },
          { label: "20:15", spend: 19, roi: 3.5, online: 5.6 },
          { label: "20:20", spend: 22, roi: 3.9, online: 6.1 },
          { label: "20:25", spend: 24, roi: 4.1, online: 6.4 },
          { label: "20:30", spend: 26, roi: 2.9, online: 6.8, flagged: true },
          { label: "20:35", spend: 28, roi: 2.6, online: 6.6, flagged: true },
          { label: "20:40", spend: 25, roi: 3.1, online: 6.2 }
        ],
        docs: [
          { id: "doc-h1", name: "家居场次复盘_2026-10-12.md", type: "MD", size: "48 KB", status: "已学习", rules: 4, date: "10/13" },
          { id: "doc-h2", name: "家居类目投放 SOP.pdf", type: "PDF", size: "1.7 MB", status: "已学习", rules: 5, date: "10/14" }
        ],
        rules: [
          "材质实验段落后 5 分钟是主要成交窗口，优先保持在线。",
          "尺码咨询超过 8 条/分钟时，暂停追投并前置尺码讲解。",
          "自然推荐 ROI 高于付费推荐时，优先追加自然承接素材。",
          "组合装计划单次加预算不超过 6%。"
        ]
      },
      select: {
        summary: { spend: 7600, spendRate: 620, roi: 3.86, orders: 142, ordersRate: 12, paidShare: 66, online: 2260, cvr: 2.72 },
        channels: [
          { name: "付费推荐", color: "#0b7a58", share: 48, spend: 462, roi: 3.4, trend: -5.2 },
          { name: "搜索", color: "#2b6f94", share: 18, spend: 174, roi: 4.0, trend: -1.8 },
          { name: "自然推荐", color: "#c9723c", share: 22, spend: 0, roi: 4.6, trend: 2.1 },
          { name: "关注", color: "#8e6a2f", share: 7, spend: 0, roi: 5.2, trend: 0.8 },
          { name: "其他", color: "#a8b3ab", share: 5, spend: 62, roi: 2.5, trend: -6.4 }
        ],
        persona: {
          gender: [["女", 91], ["男", 9]],
          age: [["25-34", 41], ["35-44", 29], ["18-24", 21], ["45+", 9]],
          region: "华东 35% · 华南 26% · 西南 16%",
          tags: ["节日礼赠", "配饰搭配", "价格对比", "快节奏浏览", "高互动"]
        },
        signals: [
          { label: "主播状态", value: "待开播 66", tone: "warn", note: "上一场后段节奏下滑" },
          { label: "日时段", value: "下午短场", tone: "warn", note: "14:00–17:00 更适合短时爆发" },
          { label: "渠道结构", value: "付费占 66%", tone: "bad", note: "自然流量弱，获客依赖付费" },
          { label: "货场承接", value: "库存 92 件", tone: "warn", note: "背景偏暗 · 互动偏弱" }
        ],
        decisions: {
          morning: { action: "暂停追投", percent: 0, confidence: 88, reason: "当前账号未开播，主播状态与货场承接都不支持放量。先用小场测试礼赠场景和价格对比，再恢复投放。", guardrail: "未开播或库存低于 100 件时不执行追投。", expected: ["消耗 0%", "ROI 持平", "等待开播"] },
          noon: { action: "暂停追投，先修复承接", percent: 0, confidence: 90, reason: "下午场自然流量弱、付费占比偏高，上一场后段节奏下滑。先补价格对比话术与礼盒展示，暂不放大预算。", guardrail: "互动率与停留恢复到近 7 场均值后再测试。", expected: ["消耗 0%", "ROI 持平", "先修复承接"] },
          evening: { action: "暂停追投，先修复承接", percent: 0, confidence: 90, reason: "当前账号未开播，付费流量占 66% 且自然推荐偏弱。建议先恢复开播，用礼赠场景和价格对比拉起自然流量。", guardrail: "未开播或 ROI 低于 3.5 时不执行追投。", expected: ["消耗 0%", "ROI 持平", "等待开播"] }
        },
        anomalies: [
          { time: "14:20–14:30", severity: "中", metric: "付费推荐占比 72%，自然流量不足", cause: "开播初期自然推荐未起量", suggestion: "先用福利款承接，增加互动与停留" },
          { time: "15:05–15:15", severity: "高", metric: "价格对比咨询集中，ROI 降至 3.1", cause: "同价位比较话术缺失", suggestion: "前置成分与同价位对比" }
        ],
        series: [
          { label: "14:00", spend: 16, roi: 3.8, online: 1.8 },
          { label: "14:05", spend: 18, roi: 3.6, online: 1.9 },
          { label: "14:10", spend: 22, roi: 3.4, online: 2.0 },
          { label: "14:15", spend: 28, roi: 3.1, online: 2.1, flagged: true },
          { label: "14:20", spend: 30, roi: 3.0, online: 2.2, flagged: true },
          { label: "14:25", spend: 26, roi: 3.3, online: 2.1 },
          { label: "14:30", spend: 24, roi: 3.7, online: 2.0 },
          { label: "14:35", spend: 21, roi: 4.0, online: 1.9 },
          { label: "14:40", spend: 19, roi: 4.2, online: 1.8 }
        ],
        docs: [
          { id: "doc-s1", name: "配饰礼赠场复盘_10月.md", type: "MD", size: "36 KB", status: "已学习", rules: 3, date: "10/15" }
        ],
        rules: [
          "礼赠场景优先展示礼盒与收礼对象，提升停留。",
          "付费占比超过 70% 时暂停加预算，先补自然流量承接。",
          "价格对比问题超过 5 条/分钟时，立即前置成分与同价位对比。"
        ]
      }
    };

    const CAMPAIGN_RULE_POOL = [
      "新文档：单场直播前 30 分钟以测试为主，放量幅度不超过 5%。",
      "新文档：ROI 连续 15 分钟低于 3.5 时，优先降低付费推荐预算。",
      "新文档：晚场 21:00 后若停留时长高于 45 秒，可追加 8%–12% 预算。",
      "新文档：自然流量占比低于 30% 时，先补互动与福利承接。",
      "新文档：一键控量后至少观察 20 分钟，再决定是否恢复预算。"
    ];

    const CAMPAIGN_ACTIONS = [
      { id: "scale-boost", title: "放量追投", desc: "提高计划预算与出价，争取更多成交。", min: 5, max: 30, value: 15, direction: 1, kind: "boost" },
      { id: "cost-boost", title: "控成本追投", desc: "提高预算但保持成本上限，适合 ROI 稳定时。", min: 5, max: 20, value: 8, direction: 1, kind: "cost" },
      { id: "scale-all", title: "一键放量", desc: "对当前优质计划批量提高预算。", min: 10, max: 50, value: 20, direction: 1, kind: "all" },
      { id: "reduce-all", title: "一键控量", desc: "对低效计划批量降低预算与出价。", min: 5, max: 30, value: 20, direction: -1, kind: "reduce" }
    ];

    const DIAG_SERIES = {};
    const DIAG_BASE_SECONDS = 20 * 3600;
    let diagBannedWords = [];
    let anchorUploadSeq = 0;
    let reviewAccountId = null;
    const svgNS = "http://www.w3.org/2000/svg";
    const $ = selector => document.querySelector(selector);
    const $$ = selector => Array.from(document.querySelectorAll(selector));
    let chartGeometry = null;
    let reviewChartGeometry = null;
    let diagChartGeometry = null;
    let resizeTimer = null;

    function sum(rows, key) {
      return rows.reduce((total, row) => total + row[key], 0);
    }

    function aggregateSeries(seriesList) {
      if (!seriesList.length) return [];
      return seriesList[0].map((row, index) => ({
        date: row.date,
        spend: seriesList.reduce((total, series) => total + series[index].spend, 0),
        gmv: seriesList.reduce((total, series) => total + series[index].gmv, 0),
        orders: seriesList.reduce((total, series) => total + series[index].orders, 0)
      }));
    }

    function getAccountById(id) {
      return ACCOUNTS.find(account => account.id === id) || ACCOUNTS[0];
    }

    function refreshActiveData() {
      ACTIVE_ACCOUNT = getAccountById(state.accountId);
      ACTIVE_DATA = state.scope === "account"
        ? ACTIVE_ACCOUNT.data
        : aggregateSeries(ACCOUNTS.map(account => account.data));
    }

    function clamp(value, min, max) {
      return Math.min(max, Math.max(min, value));
    }

    function findIndex(date, series = ACTIVE_DATA) {
      return series.findIndex(row => row.date === date);
    }

    function getRange(start, end, series = ACTIVE_DATA) {
      const startIndex = findIndex(start, series);
      const endIndex = findIndex(end, series);
      if (startIndex < 0 || endIndex < 0) return [];
      return series.slice(Math.min(startIndex, endIndex), Math.max(startIndex, endIndex) + 1);
    }

    function getPreviousRange(start, end, series = ACTIVE_DATA) {
      const startIndex = findIndex(start, series);
      const endIndex = findIndex(end, series);
      const length = Math.abs(endIndex - startIndex) + 1;
      const previousEnd = Math.min(startIndex, endIndex) - 1;
      const previousStart = previousEnd - length + 1;
      if (previousStart < 0 || previousEnd < 0) return [];
      return series.slice(previousStart, previousEnd + 1);
    }

    function formatDate(date) {
      const [year, month, day] = date.split("-");
      return `${year}.${month}.${day}`;
    }

    function formatShortDate(date) {
      const [, month, day] = date.split("-");
      return `${month}/${day}`;
    }

    function formatNumber(value, decimals) {
      if (!Number.isFinite(value)) return "—";
      return value.toLocaleString("zh-CN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      });
    }

    function formatMetric(value, metricKey, compact = false) {
      const metric = METRICS[metricKey];
      if (!Number.isFinite(value)) return "—";
      if (metric.kind === "currency") {
        if (compact && value >= 10000) return `¥${formatNumber(value / 10000, 1)}万`;
        if (compact) return `¥${formatNumber(value, 0)}`;
        return `¥${formatNumber(value, metric.decimals)}`;
      }
      if (metric.kind === "percent") return `${formatNumber(value, metric.decimals)}%`;
      return formatNumber(value, metric.decimals);
    }

    function formatDelta(value) {
      if (!Number.isFinite(value)) return "—";
      const sign = value > 0 ? "+" : "";
      return `${sign}${value.toFixed(1)}%`;
    }

    function updateDateInputs() {
      $("#startDate").value = state.start;
      $("#endDate").value = state.end;
      $("#startDate").min = ACTIVE_DATA[0].date;
      $("#startDate").max = ACTIVE_DATA[ACTIVE_DATA.length - 1].date;
      $("#endDate").min = ACTIVE_DATA[0].date;
      $("#endDate").max = ACTIVE_DATA[ACTIVE_DATA.length - 1].date;
      $$(".segmented button").forEach(button => {
        const days = Number(button.dataset.days);
        const expectedStart = ACTIVE_DATA[Math.max(0, ACTIVE_DATA.length - days)].date;
        const isActive = state.end === ACTIVE_DATA[ACTIVE_DATA.length - 1].date && state.start === expectedStart;
        button.classList.toggle("active", isActive);
      });
    }

    function renderKpis(rows, previousRows) {
      Object.entries(METRICS).forEach(([key, metric]) => {
        const card = $(`.kpi-card[data-kpi="${key}"]`);
        const currentValue = rows.length ? metric.aggregate(rows) : NaN;
        const previousValue = previousRows.length ? metric.aggregate(previousRows) : NaN;
        const shownValue = metric.display(currentValue);
        const delta = Number.isFinite(previousValue) && previousValue !== 0
          ? (currentValue / previousValue - 1) * 100
          : NaN;

        card.querySelector("[data-value]").textContent = Number.isFinite(shownValue)
          ? formatNumber(shownValue, metric.decimals)
          : "—";
        card.querySelector("[data-unit]").textContent = metric.unit;
        card.querySelector("[data-note]").textContent = metric.note;

        const deltaNode = card.querySelector("[data-delta]");
        deltaNode.textContent = Number.isFinite(delta) ? formatDelta(delta) : "—";
        deltaNode.className = "kpi-delta";
        if (Number.isFinite(delta)) {
          const isGood = metric.deltaTone === "goodUp"
            ? delta > 0
            : metric.deltaTone === "goodDown" ? delta < 0 : null;
          if (isGood === true) deltaNode.classList.add("good");
          if (isGood === false) deltaNode.classList.add("bad");
          deltaNode.title = `较上一周期 ${formatDelta(delta)}`;
        } else {
          deltaNode.removeAttribute("title");
        }

        drawSparkline(card.querySelector(".sparkline"), rows.map(metric.daily), metric.color);
      });
    }

    function drawSparkline(svg, values, color) {
      svg.replaceChildren();
      if (values.length < 2) return;
      const width = 66;
      const height = 24;
      const pad = 2;
      const min = Math.min(...values);
      const max = Math.max(...values);
      const spread = max - min || 1;
      const points = values.map((value, index) => ({
        x: pad + index / (values.length - 1) * (width - pad * 2),
        y: height - pad - (value - min) / spread * (height - pad * 2)
      }));
      const line = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
      const area = `${line} L${width - pad},${height} L${pad},${height} Z`;

      const areaNode = document.createElementNS(svgNS, "path");
      areaNode.setAttribute("d", area);
      areaNode.setAttribute("fill", color);
      areaNode.setAttribute("opacity", "0.08");
      svg.appendChild(areaNode);

      const lineNode = document.createElementNS(svgNS, "path");
      lineNode.setAttribute("d", line);
      lineNode.setAttribute("fill", "none");
      lineNode.setAttribute("stroke", color);
      lineNode.setAttribute("stroke-width", "1.5");
      lineNode.setAttribute("stroke-linecap", "round");
      lineNode.setAttribute("stroke-linejoin", "round");
      svg.appendChild(lineNode);

      const last = points[points.length - 1];
      const dot = document.createElementNS(svgNS, "circle");
      dot.setAttribute("cx", last.x);
      dot.setAttribute("cy", last.y);
      dot.setAttribute("r", "1.9");
      dot.setAttribute("fill", color);
      dot.setAttribute("stroke", "#fff");
      dot.setAttribute("stroke-width", "1");
      svg.appendChild(dot);
    }

    function median(values) {
      if (!values.length) return NaN;
      const sorted = [...values].sort((a, b) => a - b);
      const middle = Math.floor(sorted.length / 2);
      return sorted.length % 2
        ? sorted[middle]
        : (sorted[middle - 1] + sorted[middle]) / 2;
    }

    function normalizeMaterialValue(value, min, max, invert = false) {
      if (max === min) return 1;
      const normalized = (value - min) / (max - min);
      return invert ? 1 - normalized : normalized;
    }

    function getMaterialsForScope() {
      return state.scope === "total"
        ? MATERIALS
        : MATERIALS.filter(material => material.accountId === ACTIVE_ACCOUNT.id);
    }

    function scoreMaterials(materials) {
      if (!materials.length) return [];
      const spends = materials.map(material => material.spend);
      const orders = materials.map(material => material.orders);
      const clicks = materials.map(material => material.clicks);
      const impressions = materials.map(material => material.impressions);
      const spendMin = Math.min(...spends);
      const spendMax = Math.max(...spends);
      const orderMin = Math.min(...orders);
      const orderMax = Math.max(...orders);
      const clickMin = Math.min(...clicks);
      const clickMax = Math.max(...clicks);
      const impressionMin = Math.min(...impressions);
      const impressionMax = Math.max(...impressions);

      const scored = materials.map(material => {
        const spendScore = normalizeMaterialValue(material.spend, spendMin, spendMax, true);
        const orderScore = normalizeMaterialValue(material.orders, orderMin, orderMax);
        const clickScore = normalizeMaterialValue(material.clicks, clickMin, clickMax);
        const impressionScore = normalizeMaterialValue(material.impressions, impressionMin, impressionMax);
        const score = (
          spendScore * MATERIAL_WEIGHTS.spend +
          orderScore * MATERIAL_WEIGHTS.orders +
          clickScore * MATERIAL_WEIGHTS.clicks +
          impressionScore * MATERIAL_WEIGHTS.impressions
        ) / MATERIAL_WEIGHT_TOTAL * 100;
        const conversionCost = material.orders ? material.spend / material.orders : NaN;
        const roi = material.spend ? material.gmv / material.spend : NaN;
        const ctr = material.impressions ? material.clicks / material.impressions * 100 : NaN;
        return { ...material, score, conversionCost, roi, ctr };
      }).sort((a, b) => b.score - a.score);

      const medianSpend = median(scored.map(item => item.spend));
      const medianOrders = median(scored.map(item => item.orders));
      const medianCost = median(scored.map(item => item.conversionCost));
      const medianRoi = median(scored.map(item => item.roi));
      const orderCutoff = [...scored]
        .sort((a, b) => b.orders - a.orders)[Math.max(0, Math.floor(scored.length * 0.4) - 1)]
        .orders;

      scored.forEach(material => {
        const isScale = material.orders >= orderCutoff &&
          material.roi >= medianRoi &&
          material.conversionCost <= medianCost * 1.08;
        const isBoost = !isScale &&
          material.spend <= medianSpend &&
          material.orders >= medianOrders * 0.65 &&
          material.roi >= medianRoi * 0.95 &&
          material.conversionCost <= medianCost * 1.05;
        material.strategy = isScale ? "放量" : isBoost ? "追投" : "观察";
        material.verdict = material.score >= 55 ? "优质" : material.score >= 38 ? "观察" : "待优化";
      });

      return scored;
    }

    function materialTypeClass(type) {
      if (type === "图片") return "image";
      if (type === "直播切片") return "live";
      return "";
    }

    function materialTypeMark(type) {
      if (type === "图片") return "图";
      if (type === "直播切片") return "切";
      return "视";
    }

    function strategyClass(strategy) {
      if (strategy === "放量") return "scale";
      if (strategy === "追投") return "boost";
      return "watch";
    }

    function verdictClass(verdict) {
      if (verdict === "优质") return "good";
      if (verdict === "观察") return "watch";
      return "low";
    }

    function renderStrategyItems(items, container, emptyText) {
      if (!items.length) {
        container.innerHTML = `<div class="material-empty">${emptyText}</div>`;
        return;
      }
      container.innerHTML = items.map(item => `
        <div class="strategy-item">
          <div class="strategy-item-top">
            <strong>${item.name}</strong>
            <span>${item.score.toFixed(1)} 分</span>
          </div>
          <p>ROI ${item.roi.toFixed(2)} · 成本 ¥${formatNumber(item.conversionCost, 1)} · 消耗 ¥${formatNumber(item.spend, 0)} · 订单 ${item.orders}</p>
        </div>
      `).join("");
    }

    function renderMaterialPage() {
      const scored = scoreMaterials(getMaterialsForScope());
      const topTen = scored.slice(0, 10);
      const boostItems = scored.filter(item => item.strategy === "追投");
      const scaleItems = scored.filter(item => item.strategy === "放量");
      const time = lastSyncAt.toLocaleTimeString("zh-CN", { hour12: false });

      $("#topMaterialList").innerHTML = topTen.length ? topTen.map((item, index) => `
        <div class="top-material-row${index === 0 ? " top-1" : ""}">
          <span class="top-rank${index === 0 ? " top-1" : ""}">${String(index + 1).padStart(2, "0")}</span>
          <span class="material-thumb ${materialTypeClass(item.type)}">${materialTypeMark(item.type)}</span>
          <span class="top-material-main">
            <span class="top-material-name">${item.name}</span>
            <span class="top-material-sub">${item.type} · ${item.id} · ${item.persona.age} · ${item.persona.region} · ${item.persona.gender}</span>
          </span>
          <span class="top-material-score"><strong>${item.score.toFixed(1)}</strong><span>综合分</span></span>
          <span class="top-material-metrics"><strong>¥${formatNumber(item.spend, 0)}</strong> 消耗<br><strong>${item.orders}</strong> 订单</span>
        </div>
      `).join("") : `<div class="material-empty">当前范围暂无素材</div>`;

      $("#boostCount").textContent = `${boostItems.length} 条`;
      $("#scaleCount").textContent = `${scaleItems.length} 条`;
      renderStrategyItems(boostItems, $("#boostList"), "当前范围暂无适合追投的素材");
      renderStrategyItems(scaleItems, $("#scaleList"), "当前范围暂无适合放量的素材");

      const query = ($("#materialSearch").value || "").trim().toLowerCase();
      const type = $("#materialType").value || "all";
      const filtered = scored.filter(item => {
        const typeMatch = type === "all" || item.type === type;
        const haystack = `${item.name} ${item.id} ${item.type} ${item.persona.age} ${item.persona.region} ${item.persona.gender}`.toLowerCase();
        return typeMatch && (!query || haystack.includes(query));
      });

      $("#materialTableBody").innerHTML = filtered.length ? filtered.map(item => `
        <tr>
          <td>
            <div class="table-material">
              <span class="material-thumb ${materialTypeClass(item.type)}">${materialTypeMark(item.type)}</span>
              <span>
                <span class="table-material-name">${item.name}</span>
                <span class="table-material-sub">${item.type} · ${item.id} · ${item.duration}</span>
              </span>
            </div>
          </td>
          <td>¥${formatNumber(item.spend, 0)}</td>
          <td>${formatNumber(item.impressions, 0)}</td>
          <td>${formatNumber(item.clicks, 0)}</td>
          <td>${item.ctr.toFixed(2)}%</td>
          <td>${Number.isFinite(item.completionRate) ? `${item.completionRate.toFixed(1)}%` : "—"}</td>
          <td>${item.orders}</td>
          <td>¥${formatNumber(item.conversionCost, 1)}</td>
          <td>${item.dwellTime.toFixed(1)}s</td>
          <td>${item.roi.toFixed(2)}</td>
          <td class="table-score">${item.score.toFixed(1)}</td>
          <td><span class="quality-badge ${verdictClass(item.verdict)}">${item.verdict}</span></td>
          <td><span class="strategy-badge ${strategyClass(item.strategy)}">${item.strategy}</span></td>
          <td class="persona-cell">
            <strong>${item.persona.age} 岁 · ${item.persona.region} · ${item.persona.gender}性</strong>
            <span>点击 ${formatNumber(item.clicks, 0)} 次</span>
          </td>
        </tr>
      `).join("") : `<tr><td colspan="14"><div class="material-empty">没有匹配的素材</div></td></tr>`;

      const scopeText = state.scope === "total" ? "总看板" : ACTIVE_ACCOUNT.name;
      $("#materialUpdatedAt").textContent = `实时更新 · ${time}`;
      $("#materialTableFoot").textContent = `显示 ${filtered.length} / ${scored.length} 条素材 · 当前范围：${scopeText}`;
    }

    const VIEWER_PERSONA_TEMPLATES = [
      { age: "25-34", region: "华东", gender: "女" },
      { age: "24-30", region: "华南", gender: "女" },
      { age: "31-40", region: "华北", gender: "女" },
      { age: "18-23", region: "华中", gender: "女" },
      { age: "25-34", region: "西南", gender: "男" }
    ];

    const BUYER_PERSONA_TEMPLATES = [
      { age: "24-30", region: "华东", gender: "女" },
      { age: "25-34", region: "华南", gender: "女" },
      { age: "31-40", region: "华北", gender: "女" },
      { age: "18-23", region: "华中", gender: "女" },
      { age: "35-44", region: "华东", gender: "女" }
    ];

    const reviewMinuteCache = new Map();

    function formatClockShort(seconds) {
      const safe = Math.max(0, Math.floor(seconds || 0));
      const hours = String(Math.floor(safe / 3600)).padStart(2, "0");
      const minutes = String(Math.floor(safe % 3600 / 60)).padStart(2, "0");
      return `${hours}:${minutes}`;
    }

    function formatFileSize(bytes) {
      if (!Number.isFinite(bytes) || bytes <= 0) return "—";
      if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
      return `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
    }

    function resampleSeries(values, length) {
      if (!values.length || length <= 0) return Array(length).fill(0);
      if (values.length === length) return values.slice();
      if (length === 1) return [values[values.length - 1]];
      return Array.from({ length }, (_, index) => {
        const position = index / (length - 1) * (values.length - 1);
        const low = Math.floor(position);
        const high = Math.min(values.length - 1, low + 1);
        const ratio = position - low;
        return values[low] * (1 - ratio) + values[high] * ratio;
      });
    }

    function buildMinuteReviewSeries(session) {
      const minuteCount = Math.ceil(session.durationSeconds / 60);
      const annotationByMinute = new Map();
      session.annotations.forEach(annotation => {
        annotationByMinute.set(Math.floor(annotation.time / 60), annotation);
      });
      const raw = [];

      for (let minute = 0; minute < minuteCount; minute += 1) {
        const annotation = annotationByMinute.get(minute) || null;
        let script = 62 + Math.sin(minute / 8) * 8 + Math.cos(minute / 21) * 4;
        let traffic = 58 + Math.sin(minute / 10 + 1) * 9 + Math.cos(minute / 29) * 4;
        if (annotation) {
          if (annotation.type === "problem") {
            script -= 16;
            traffic -= 8;
          } else {
            script += 16;
            traffic += 11;
          }
        }
        script = clamp(script, 18, 96);
        traffic = clamp(traffic, 20, 95);

        const viewerTemplate = VIEWER_PERSONA_TEMPLATES[Math.floor(minute / 18) % VIEWER_PERSONA_TEMPLATES.length];
        const buyerTemplate = BUYER_PERSONA_TEMPLATES[Math.floor(minute / 22 + 1) % BUYER_PERSONA_TEMPLATES.length];
        const viewers = Math.round(80 + traffic * 2.7 + Math.sin(minute / 7) * 14);
        const clicks = Math.round(viewers * (0.028 + script / 100 * 0.022));
        const weighted = (script * 0.5 + traffic * 0.5) * (0.8 + Math.sin(minute / 9 + 2) * 0.12);
        const scriptLabel = annotation
          ? (annotation.type === "problem" ? "劣势话术" : "优势话术")
          : script >= 65 ? "优势话术" : script <= 50 ? "劣势话术" : "话术中性";
        const trafficLabel = traffic >= 65 ? "流量好" : traffic <= 50 ? "流量差" : "流量一般";
        const scriptNote = annotation
          ? annotation.desc
          : script >= 65
            ? "卖点表达清晰，讲解节奏稳定，能承接流量。"
            : script <= 50
              ? "话术进入重复段，卖点密度下降，转化承压。"
              : "话术节奏平稳，未出现明显波动。";
        const trafficNote = annotation
          ? (annotation.type === "advantage"
            ? "该时段流量质量与话术节奏同步改善。"
            : "该时段流量增加，但成交承接效率下降。")
          : traffic >= 65
            ? "流量质量较好，进入人群与素材匹配。"
            : traffic <= 50
              ? "流量偏泛，观看上升但订单未同步。"
              : "流量质量平稳。";

        raw.push({
          minute,
          time: minute * 60,
          script,
          traffic,
          viewers,
          clicks,
          weighted,
          annotation,
          scriptLabel,
          trafficLabel,
          scriptNote,
          trafficNote,
          viewerPersona: { ...viewerTemplate, viewers, clicks },
          buyerPersona: { ...buyerTemplate, orders: 0 }
        });
      }

      const totalWeight = raw.reduce((total, point) => total + point.weighted, 0) || 1;
      const targetOrders = session.metrics?.orders || LIVE_MONITORS[session.accountId]?.metrics.orders || 100;
      const scale = targetOrders / totalWeight;
      let assigned = 0;
      raw.forEach((point, index) => {
        const orders = index === raw.length - 1
          ? Math.max(0, targetOrders - assigned)
          : Math.round(point.weighted * scale);
        point.orders = orders;
        point.buyerPersona.orders = orders;
        assigned += orders;
      });
      return raw;
    }

    function getReviewMinuteSeries(session) {
      if (!reviewMinuteCache.has(session.id)) {
        reviewMinuteCache.set(session.id, buildMinuteReviewSeries(session));
      }
      return reviewMinuteCache.get(session.id);
    }

    function getReviewBuckets(session, granularity) {
      const minutes = getReviewMinuteSeries(session);
      const buckets = [];
      for (let start = 0; start < minutes.length; start += granularity) {
        const group = minutes.slice(start, start + granularity);
        const annotationPoint = group.find(point => point.annotation);
        const buyerSource = group.reduce((best, point) => point.orders > best.orders ? point : best, group[0]);
        const script = group.reduce((total, point) => total + point.script, 0) / group.length;
        const traffic = group.reduce((total, point) => total + point.traffic, 0) / group.length;
        const orders = group.reduce((total, point) => total + point.orders, 0);
        const viewers = group.reduce((total, point) => total + point.viewers, 0);
        const clicks = group.reduce((total, point) => total + point.clicks, 0);
        const annotation = annotationPoint?.annotation || null;
        const scriptLabel = annotation
          ? (annotation.type === "problem" ? "劣势话术" : "优势话术")
          : script >= 65 ? "优势话术" : script <= 50 ? "劣势话术" : "话术中性";
        const trafficLabel = traffic >= 65 ? "流量好" : traffic <= 50 ? "流量差" : "流量一般";

        buckets.push({
          id: `${session.id}-${start}`,
          start: group[0].time,
          end: group[group.length - 1].time + 60,
          script,
          traffic,
          orders,
          viewers,
          clicks,
          annotation,
          scriptLabel,
          trafficLabel,
          scriptNote: annotation
            ? annotation.desc
            : script >= 65
              ? "卖点表达清晰，讲解节奏稳定，能承接流量。"
              : script <= 50
                ? "话术进入重复段，卖点密度下降，转化承压。"
                : "话术节奏平稳，未出现明显波动。",
          trafficNote: annotation
            ? (annotation.type === "advantage"
              ? "该时段流量质量与话术节奏同步改善。"
              : "该时段流量增加，但成交承接效率下降。")
            : traffic >= 65
              ? "流量质量较好，进入人群与素材匹配。"
              : traffic <= 50
                ? "流量偏泛，观看上升但订单未同步。"
                : "流量质量平稳。",
          viewerPersona: {
            ...(annotationPoint?.viewerPersona || group[0].viewerPersona),
            viewers,
            clicks
          },
          buyerPersona: {
            ...buyerSource.buyerPersona,
            orders
          }
        });
      }
      return buckets;
    }

    function formatClock(seconds) {
      const safe = Math.max(0, Math.floor(seconds || 0));
      const hours = String(Math.floor(safe / 3600)).padStart(2, "0");
      const minutes = String(Math.floor(safe % 3600 / 60)).padStart(2, "0");
      const rest = String(safe % 60).padStart(2, "0");
      return `${hours}:${minutes}:${rest}`;
    }

    function getReviewSessions() {
      return REVIEW_SESSIONS.filter(session => session.accountId === ACTIVE_ACCOUNT.id);
    }

    function getSelectedSession() {
      const sessions = getReviewSessions();
      return sessions.find(session => session.id === state.selectedSessionId) || sessions[0] || null;
    }

    function ensureReviewState() {
      const monitor = LIVE_MONITORS[ACTIVE_ACCOUNT.id];
      const sessions = getReviewSessions();
      if (reviewAccountId !== ACTIVE_ACCOUNT.id) {
        reviewAccountId = ACTIVE_ACCOUNT.id;
        state.selectedSessionId = sessions[0]?.id || null;
        state.playerTime = 0;
        state.playerPlaying = false;
        state.activeAnnotationId = null;
        state.recording = Boolean(monitor.live);
        state.recordSeconds = monitor.recordSeconds;
      }
      if (!state.selectedSessionId || !sessions.some(session => session.id === state.selectedSessionId)) {
        state.selectedSessionId = sessions[0]?.id || null;
        state.playerTime = 0;
        state.playerPlaying = false;
        state.activeAnnotationId = null;
      }
    }

    function updateRecordStatus() {
      const monitor = LIVE_MONITORS[ACTIVE_ACCOUNT.id];
      const status = $("#recordStatus");
      const button = $("#reviewRecordBtn");
      if (!monitor.live) {
        status.className = "record-status offline";
        status.innerHTML = "<i></i>已结束";
        button.textContent = "未开播";
        button.disabled = true;
        return;
      }
      button.disabled = false;
      button.textContent = state.recording ? "暂停录制" : "开始录制";
      if (state.recording) {
        status.className = "record-status";
        status.innerHTML = `<i></i>录制中 ${formatClock(state.recordSeconds)}`;
      } else {
        status.className = "record-status paused";
        status.innerHTML = "<i></i>录制已暂停";
      }
    }

    function renderMonitor(monitor) {
      $("#monitorTitle").textContent = monitor.title;
      $("#monitorSub").textContent = `${ACTIVE_ACCOUNT.name} · 开播 ${monitor.startTime} · ${monitor.live ? "直播中" : "已结束"}`;

      const kpis = [
        ["在线人数", formatNumber(monitor.metrics.viewers, 0), "当前"],
        ["实时消耗", `¥${formatNumber(monitor.metrics.spend, 0)}`, "本场累计"],
        ["成交订单", formatNumber(monitor.metrics.orders, 0), "本场累计"],
        ["ROI", monitor.metrics.roi.toFixed(2), "实时"],
        ["转化率", `${monitor.metrics.cvr.toFixed(2)}%`, "订单 ÷ 观看"],
        ["平均停留", `${monitor.metrics.dwell.toFixed(1)}s`, "近 30 分钟"]
      ];
      $("#monitorKpis").innerHTML = kpis.map(([label, value, note]) => `
        <div class="monitor-kpi"><span>${label}</span><strong>${value}</strong><small>${note}</small></div>
      `).join("");

      const maxBar = Math.max(...monitor.bars.map(item => item.value));
      $("#monitorBars").innerHTML = monitor.bars.map(item => `
        <div class="monitor-bar-item">
          <span class="monitor-bar" style="height:${Math.max(8, Math.round(item.value / maxBar * 72))}px"></span>
          <strong>${item.value}</strong>
          <span>${item.label}</span>
        </div>
      `).join("");

      const typeLabel = { problem: "问题", advantage: "优势", note: "提醒" };
      $("#monitorEvents").innerHTML = monitor.events.map(event => `
        <div class="event-item">
          <div class="event-item-top">
            <span class="event-time">${event.time}</span>
            <span class="event-type ${event.type}">${typeLabel[event.type]}</span>
          </div>
          <strong>${event.title}</strong>
          <p>${event.desc}</p>
        </div>
      `).join("");

      $("#monitorSessionInfo").innerHTML = `
        <div class="context-row"><span>开播账号</span><strong>${ACTIVE_ACCOUNT.name}</strong></div>
        <div class="context-row"><span>抖音号</span><strong>${ACTIVE_ACCOUNT.handle}</strong></div>
        <div class="context-row"><span>千川账户</span><strong>${ACTIVE_ACCOUNT.qianchuanId}</strong></div>
        <div class="context-row"><span>开播时间</span><strong>${monitor.startTime}</strong></div>
        <div class="context-row"><span>录制时长</span><strong>${formatClock(state.recordSeconds)}</strong></div>
        <div class="context-row"><span>直播状态</span><strong>${monitor.live ? "直播中" : "已结束"}</strong></div>
      `;
    }

    function renderAnchorPage() {
      const profile = ANCHOR_PROFILES[ACTIVE_ACCOUNT.id];
      const uploads = ANCHOR_UPLOADS[profile.accountId] || [];
      $("#anchorSwitcher").innerHTML = ACCOUNTS.map(account => {
        const host = ANCHOR_PROFILES[account.id];
        return `
          <button type="button" class="host-chip${host.accountId === profile.accountId ? " active" : ""}" data-host-account="${account.id}">
            <span class="host-chip-avatar">${host.avatar}</span>
            <span class="host-chip-main">
              <strong>${host.name}</strong>
              <span>${host.tags[0]} · ${host.totalSessions} 场 · 样貌 ${host.faceConfidence}%</span>
            </span>
          </button>
        `;
      }).join("");

      $("#anchorAvatar").textContent = profile.avatar;
      $("#anchorName").textContent = profile.name;
      $("#anchorMeta").textContent = `${profile.anchorId} · ${profile.gender} · ${profile.age} 岁 · ${ACTIVE_ACCOUNT.handle} · ${ACTIVE_ACCOUNT.qianchuanId}`;
      $("#anchorTags").innerHTML = profile.tags.map(tag => `<span class="anchor-tag">${tag}</span>`).join("");
      $("#anchorStatus").textContent = ACTIVE_ACCOUNT.status;
      $("#anchorStatus").className = `anchor-status${ACTIVE_ACCOUNT.status === "直播中" ? "" : " offline"}`;

      const info = [
        ["直播经验", profile.experience],
        ["累计场次", `${profile.totalSessions} 场`],
        ["擅长类目", profile.category],
        ["平均停留", `${profile.avgDwell.toFixed(1)}s`],
        ["主播 ID", profile.anchorId],
        ["年龄 / 性别", `${profile.age} 岁 / ${profile.gender}`]
      ];
      $("#anchorInfoGrid").innerHTML = info.map(([label, value]) => `
        <div class="anchor-info-item"><span>${label}</span><strong>${value}</strong></div>
      `).join("");

      $("#anchorStyleBars").innerHTML = profile.style.map(item => `
        <div class="style-row">
          <span>${item.label}</span>
          <span class="style-track"><span class="style-fill" style="width:${item.value}%"></span></span>
          <span class="style-value">${item.value}</span>
        </div>
      `).join("");

      $("#anchorStateGrid").innerHTML = profile.state.map(item => `
        <div class="state-item ${item.tone || ""}">
          <span>${item.label}</span>
          <strong>${item.value}</strong>
          <em>${item.note}</em>
        </div>
      `).join("");

      const statusLabel = { uploading: "上传中", analyzing: "分析中", done: "已分析", error: "失败" };
      $("#anchorUploadList").innerHTML = uploads.length ? uploads.map(upload => `
        <div class="upload-item">
          <span class="upload-item-icon">VID</span>
          <div class="upload-item-main">
            <div class="upload-item-head">
              <strong>${upload.name}</strong>
              <span>${formatFileSize(upload.size)}</span>
            </div>
            <div class="upload-item-meta">${upload.tag || upload.note || "等待分析"}</div>
            <div class="progress-track"><span style="width:${Math.round(upload.progress || 0)}%"></span></div>
          </div>
          <span class="upload-status ${upload.status}">${statusLabel[upload.status] || "处理中"}</span>
        </div>
      `).join("") : `<div class="material-empty">暂无新增录屏，可上传历史直播录屏用于学习</div>`;

      $("#anchorConfidence").textContent = `${Math.round(profile.confidence)}%`;
      $("#anchorProgress").style.width = `${profile.confidence}%`;
      $("#anchorLearningNote").textContent = `已学习 ${profile.learnedSessions} 场 · ${profile.learnedHours.toFixed(1)} 小时 · 模型持续更新`;

      $("#anchorRecommendations").innerHTML = `
        <div class="match-item">
          <span>最佳开播时段</span>
          <strong>${profile.bestTime}</strong>
          <p>${profile.bestTimeReason}</p>
        </div>
        <div class="match-item">
          <span>推荐话术组合</span>
          <div class="match-tags">${profile.scriptMatch.map(item => `<span>${item}</span>`).join("")}</div>
        </div>
        <div class="match-item">
          <span>历史出单高峰</span>
          <strong>${profile.peakWindows.join(" / ")}</strong>
          <p>基于主播库历史录屏与当前账号表现综合得出。</p>
        </div>
      `;

      $("#anchorInsight").textContent = profile.insight;
      $("#anchorRhythm").innerHTML = profile.orderRhythm.map((value, index) => `
        <div class="anchor-rhythm-item">
          <span class="anchor-rhythm-bar" style="height:${Math.round(value * 0.8)}px"></span>
          <span>${index * 10}-${(index + 1) * 10}m</span>
        </div>
      `).join("");
      $("#anchorRhythmFoot").textContent = `高峰：${profile.peakWindows.join("、")} · 基于 ${profile.learnedSessions} 场历史录屏`;
      $("#anchorFaceNote").textContent = `样貌匹配 ${profile.faceConfidence}% · 已进入主播库`;
    }

    function handleAnchorFiles(fileList) {
      const files = Array.from(fileList || []);
      const videos = files.filter(file => file.type.startsWith("video/") || /\.(mp4|mov|m4v|webm)$/i.test(file.name));
      if (!videos.length) {
        $("#anchorLearningNote").textContent = "请选择 MP4 / MOV 等视频文件";
        return;
      }

      const accountId = ACTIVE_ACCOUNT.id;
      const profile = ANCHOR_PROFILES[accountId];
      const uploads = ANCHOR_UPLOADS[accountId];
      videos.forEach((file, index) => {
        const upload = {
          id: `upload-${Date.now()}-${anchorUploadSeq++}`,
          name: file.name,
          size: file.size,
          status: "uploading",
          progress: 0,
          tag: "",
          note: "上传中"
        };
        uploads.unshift(upload);
        if (state.view === "review" && state.reviewTab === "anchor" && state.accountId === accountId) renderAnchorPage();

        let progress = 0;
        const uploadTimer = window.setInterval(() => {
          progress = Math.min(100, progress + 18);
          upload.progress = progress;
          upload.note = progress < 100 ? `上传中 ${progress}%` : "提取话术、状态与出单节奏";
          if (state.view === "review" && state.reviewTab === "anchor" && state.accountId === accountId) renderAnchorPage();
          if (progress >= 100) {
            window.clearInterval(uploadTimer);
            upload.status = "analyzing";
            if (state.view === "review" && state.reviewTab === "anchor" && state.accountId === accountId) renderAnchorPage();
            window.setTimeout(() => {
              const tags = ["亲和互动", "节奏偏快", "专业讲解", "情绪饱满"];
              const tag = tags[(file.name.length + index) % tags.length];
              upload.status = "done";
              upload.progress = 100;
              upload.tag = `新增特征：${tag}`;
              upload.note = "已加入风格模型";
              profile.learnedSessions += 1;
              profile.learnedHours += Math.max(0.4, file.size / (1024 * 1024 * 120));
              profile.confidence = Math.min(97, profile.confidence + 0.7);
              if (!profile.tags.includes(tag)) profile.tags.push(tag);
              if (state.view === "review" && state.reviewTab === "anchor" && state.accountId === accountId) renderAnchorPage();
            }, 800);
          }
        }, 220);
      });
    }

    function renderReviewChart(session) {
      const svg = $("#reviewChart");
      const wrap = $("#reviewChartWrap");
      const tooltip = $("#reviewChartTooltip");
      svg.replaceChildren();
      tooltip.hidden = true;
      reviewChartGeometry = null;
      if (!session) return;

      const buckets = getReviewBuckets(session, state.reviewGranularity);
      if (!buckets.length) return;
      const anchor = ANCHOR_PROFILES[ACTIVE_ACCOUNT.id];
      const historyValues = resampleSeries(anchor.orderRhythm, buckets.length);
      const width = Math.max(320, wrap.clientWidth || 640);
      const height = Math.max(240, wrap.clientHeight || 288);
      const margin = { top: 18, right: 18, bottom: 30, left: 38 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const orderValues = buckets.map(bucket => bucket.orders);
      const displayOrders = state.reviewGranularity === 1
        ? orderValues.map((value, index) => {
          let total = 0;
          let count = 0;
          for (let offset = -2; offset <= 2; offset += 1) {
            const neighbor = orderValues[index + offset];
            if (Number.isFinite(neighbor)) {
              total += neighbor;
              count += 1;
            }
          }
          return total / Math.max(1, count);
        })
        : orderValues;
      const maxDisplayOrders = Math.max(...displayOrders, 1);
      const xFor = index => margin.left + (buckets.length === 1 ? innerWidth / 2 : index / (buckets.length - 1) * innerWidth);
      const yFor = value => margin.top + (100 - value) / 100 * innerHeight;

      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      svg.setAttribute("aria-label", `话术与流量复盘曲线，${state.reviewGranularity}分钟颗粒度`);

      for (let index = 0; index <= 4; index += 1) {
        const y = margin.top + innerHeight / 4 * index;
        const value = 100 - index * 25;
        svg.appendChild(svgElement("line", {
          x1: margin.left,
          y1: y,
          x2: width - margin.right,
          y2: y,
          stroke: "#e8ece7",
          "stroke-width": "1",
          "stroke-dasharray": index === 4 ? "0" : "2 4"
        }));
        const label = svgElement("text", {
          x: margin.left - 8,
          y: y + 3.5,
          "text-anchor": "end",
          fill: "#8a978f",
          "font-size": "9",
          "font-variant-numeric": "tabular-nums"
        });
        label.textContent = String(value);
        svg.appendChild(label);
      }

      const labelCount = Math.min(buckets.length, width < 700 ? 4 : 6);
      const labelIndexes = new Set();
      for (let index = 0; index < labelCount; index += 1) {
        labelIndexes.add(Math.round(index / Math.max(1, labelCount - 1) * (buckets.length - 1)));
      }
      labelIndexes.add(buckets.length - 1);
      labelIndexes.forEach((index, order) => {
        const label = svgElement("text", {
          x: xFor(index),
          y: height - 9,
          "text-anchor": order === 0 ? "start" : index === buckets.length - 1 ? "end" : "middle",
          fill: "#8a978f",
          "font-size": "9"
        });
        label.textContent = formatClockShort(buckets[index].start);
        svg.appendChild(label);
      });

      const pathFor = valueFor => buckets.map((bucket, index) => {
        const value = valueFor(bucket);
        return `${index ? "L" : "M"}${xFor(index).toFixed(1)},${yFor(value).toFixed(1)}`;
      }).join(" ");

      svg.appendChild(svgElement("path", {
        d: pathFor(bucket => bucket.script),
        fill: "none",
        stroke: "#0b7a58",
        "stroke-width": "2.1",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      }));
      svg.appendChild(svgElement("path", {
        d: pathFor(bucket => bucket.traffic),
        fill: "none",
        stroke: "#2b6f94",
        "stroke-width": "2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      }));
      svg.appendChild(svgElement("path", {
        d: displayOrders.map((value, index) => `${index ? "L" : "M"}${xFor(index).toFixed(1)},${yFor(value / maxDisplayOrders * 100).toFixed(1)}`).join(" "),
        fill: "none",
        stroke: "#c9723c",
        "stroke-width": "1.5",
        "stroke-dasharray": "4 3",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      }));
      svg.appendChild(svgElement("path", {
        d: historyValues.map((value, index) => `${index ? "L" : "M"}${xFor(index).toFixed(1)},${yFor(value).toFixed(1)}`).join(" "),
        fill: "none",
        stroke: "#9b8ac4",
        "stroke-width": "1.4",
        "stroke-dasharray": "3 4",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        opacity: "0.9"
      }));

      if (buckets.length <= 60) {
        buckets.forEach((bucket, index) => {
          svg.appendChild(svgElement("circle", {
            cx: xFor(index),
            cy: yFor(bucket.script),
            r: "1.5",
            fill: "#0b7a58",
            opacity: "0.45"
          }));
        });
      }

      buckets.forEach((bucket, index) => {
        if (!bucket.annotation) return;
        svg.appendChild(svgElement("circle", {
          cx: xFor(index),
          cy: yFor(bucket.script),
          r: "4.6",
          fill: bucket.annotation.type === "problem" ? "#c9723c" : "#0b7a58",
          stroke: "#fff",
          "stroke-width": "2"
        }));
      });

      const hoverLine = svgElement("line", {
        x1: 0,
        y1: margin.top,
        x2: 0,
        y2: margin.top + innerHeight,
        stroke: "#8ca097",
        "stroke-width": "1",
        "stroke-dasharray": "3 3",
        opacity: "0"
      });
      const hoverDot = svgElement("circle", {
        cx: 0,
        cy: 0,
        r: "4.2",
        fill: "#0b7a58",
        stroke: "#fff",
        "stroke-width": "2",
        opacity: "0"
      });
      svg.append(hoverLine, hoverDot);

      const keyBuckets = buckets
        .map((bucket, index) => ({ bucket, index }))
        .filter(item => Boolean(item.bucket.annotation));
      const railScale = (wrap.clientWidth || width) / width;
      $("#reviewPointRail").innerHTML = keyBuckets.map(item => `
        <button type="button" class="review-point ${item.bucket.annotation.type}" style="left:${(xFor(item.index) * railScale).toFixed(1)}px" data-bucket-index="${item.index}" title="${formatClockShort(item.bucket.start)} ${item.bucket.annotation.title}">
          <span class="review-point-dot"></span>
          <span class="review-point-time">${formatClockShort(item.bucket.start)}</span>
        </button>
      `).join("");
      $$("#reviewPointRail [data-bucket-index]").forEach(button => {
        const index = Number(button.dataset.bucketIndex);
        const show = () => showReviewChartTooltip(buckets[index], index, button);
        button.addEventListener("pointerenter", show);
        button.addEventListener("focus", show);
        button.addEventListener("click", show);
        button.addEventListener("pointerleave", hideReviewChartTooltip);
        button.addEventListener("blur", hideReviewChartTooltip);
      });

      $("#reviewChartMeta").textContent = `当前粒度 ${state.reviewGranularity} 分钟 · ${buckets.length} 个点 · ${keyBuckets.length} 个关键标注`;
      $$(".granularity-tabs button").forEach(button => {
        button.classList.toggle("active", Number(button.dataset.granularity) === state.reviewGranularity);
      });

      reviewChartGeometry = {
        buckets,
        width,
        height,
        margin,
        innerWidth,
        xFor,
        yFor,
        hoverLine,
        hoverDot,
        historyValues,
        displayOrders,
        maxDisplayOrders
      };
    }

    function showReviewChartTooltip(bucket, index, sourceElement = null) {
      if (!reviewChartGeometry) return;
      const tooltip = $("#reviewChartTooltip");
      const panel = $(".review-chart-panel");
      const wrap = $("#reviewChartWrap");
      const geometry = reviewChartGeometry;
      const scriptTone = bucket.scriptLabel === "优势话术" ? "good" : bucket.scriptLabel === "劣势话术" ? "bad" : "neutral";
      const trafficTone = bucket.trafficLabel === "流量好" ? "good" : bucket.trafficLabel === "流量差" ? "bad" : "neutral";
      const orderIndex = Math.round((geometry.displayOrders[index] || 0) / Math.max(1, geometry.maxDisplayOrders) * 100);
      const historyIndex = Math.round(geometry.historyValues[index] || 0);
      const historyGap = orderIndex - historyIndex;

      tooltip.innerHTML = `
        <div class="review-tooltip-head">
          <span>${formatClockShort(bucket.start)} — ${formatClockShort(bucket.end)}</span>
          <span>${state.reviewGranularity} 分钟</span>
        </div>
        <div class="review-tooltip-tags">
          <span class="review-tooltip-tag ${scriptTone}">${bucket.scriptLabel}</span>
          <span class="review-tooltip-tag ${trafficTone}">${bucket.trafficLabel}</span>
        </div>
        <div class="review-tooltip-grid">
          <div><span>话术影响</span><strong>${Math.round(bucket.script)}</strong></div>
          <div><span>流量质量</span><strong>${Math.round(bucket.traffic)}</strong></div>
          <div><span>成交表现 · ${bucket.orders} 单</span><strong>${orderIndex}</strong></div>
        </div>
        <div class="review-tooltip-note"><span>话术</span><p>${bucket.scriptNote}</p></div>
        <div class="review-tooltip-note"><span>流量</span><p>${bucket.trafficNote}</p></div>
        <div class="review-tooltip-note"><span>历史对照</span><p>当前成交表现 ${orderIndex}，历史同期 ${historyIndex}，${historyGap >= 0 ? "高" : "低"} ${Math.abs(historyGap)} 点。</p></div>
        <div class="review-tooltip-persona">
          <span>当时人群</span>
          <strong>${bucket.viewerPersona.age} 岁 · ${bucket.viewerPersona.region} · ${bucket.viewerPersona.gender}性</strong>
          <em>观看 ${formatNumber(bucket.viewers, 0)} · 点击 ${formatNumber(bucket.clicks, 0)}</em>
        </div>
        <div class="review-tooltip-persona">
          <span>拍下产品人群</span>
          <strong>${bucket.buyerPersona.age} 岁 · ${bucket.buyerPersona.region} · ${bucket.buyerPersona.gender}性</strong>
          <em>成交 ${formatNumber(bucket.buyerPersona.orders, 0)} 单</em>
        </div>
      `;

      const panelRect = panel.getBoundingClientRect();
      const wrapRect = wrap.getBoundingClientRect();
      let left;
      let top;
      if (sourceElement) {
        const sourceRect = sourceElement.getBoundingClientRect();
        left = sourceRect.left - panelRect.left + sourceRect.width / 2;
        top = sourceRect.bottom - panelRect.top;
      } else {
        const x = geometry.xFor(index) / geometry.width * wrapRect.width;
        left = wrapRect.left - panelRect.left + x;
        top = wrapRect.bottom - panelRect.top - 4;
      }
      const half = Math.min(165, panelRect.width / 2 - 8);
      tooltip.style.left = `${clamp(left, half, panelRect.width - half)}px`;
      tooltip.style.top = `${Math.max(220, top)}px`;
      tooltip.hidden = false;
    }

    function hideReviewChartTooltip() {
      const tooltip = $("#reviewChartTooltip");
      if (tooltip) tooltip.hidden = true;
      if (reviewChartGeometry) {
        reviewChartGeometry.hoverLine.setAttribute("opacity", "0");
        reviewChartGeometry.hoverDot.setAttribute("opacity", "0");
      }
    }

    function handleReviewChartPointer(event) {
      if (!reviewChartGeometry) return;
      const geometry = reviewChartGeometry;
      const svg = $("#reviewChart");
      const rect = svg.getBoundingClientRect();
      const pointerX = (event.clientX - rect.left) * (geometry.width / rect.width);
      const ratio = clamp((pointerX - geometry.margin.left) / geometry.innerWidth, 0, 1);
      const index = Math.round(ratio * Math.max(0, geometry.buckets.length - 1));
      const bucket = geometry.buckets[index];
      const x = geometry.xFor(index);
      const y = geometry.yFor(bucket.script);
      geometry.hoverLine.setAttribute("x1", x);
      geometry.hoverLine.setAttribute("x2", x);
      geometry.hoverLine.setAttribute("opacity", "1");
      geometry.hoverDot.setAttribute("cx", x);
      geometry.hoverDot.setAttribute("cy", y);
      geometry.hoverDot.setAttribute("opacity", "1");
      showReviewChartTooltip(bucket, index);
    }

    function renderPlayback() {
      const sessions = getReviewSessions();
      const session = getSelectedSession();
      if (!session) {
        $("#sessionList").innerHTML = `<div class="material-empty">当前账号暂无直播场次</div>`;
        $("#annotationList").innerHTML = `<div class="material-empty">暂无标注</div>`;
        return;
      }
      state.playerTime = clamp(state.playerTime, 0, session.durationSeconds);
      const annotationTypes = { problem: "问题", advantage: "优势" };
      const problems = session.annotations.filter(item => item.type === "problem").length;
      const advantages = session.annotations.filter(item => item.type === "advantage").length;
      const activeAnnotation = session.annotations.find(item => item.id === state.activeAnnotationId);
      const anchor = ANCHOR_PROFILES[ACTIVE_ACCOUNT.id];

      $("#playerTitle").textContent = `${session.title} · ${session.date}`;
      $("#faceMatchName").textContent = anchor.name;
      $("#faceMatchScore").textContent = `${anchor.faceConfidence}%`;
      $("#reviewChartAnchorText").textContent = `已匹配主播 ${anchor.name} · 样貌 ${anchor.faceConfidence}% · 已学习 ${anchor.learnedSessions} 场`;
      $("#reviewAnchorName").textContent = anchor.name;
      $("#reviewAnchorNote").textContent = anchor.reviewLinkNote;
      $("#sessionCount").textContent = `${sessions.length} 场`;
      $("#annotationCount").textContent = `${session.annotations.length} 条`;

      $("#sessionList").innerHTML = sessions.map(item => {
        const issueCount = item.annotations.filter(annotation => annotation.type === "problem").length;
        const goodCount = item.annotations.filter(annotation => annotation.type === "advantage").length;
        return `
          <button type="button" class="session-item${item.id === session.id ? " active" : ""}" data-session-id="${item.id}">
            <div class="session-item-top">
              <strong>${item.title}</strong>
              <span>${formatClock(item.durationSeconds)}</span>
            </div>
            <p>${item.date} · 问题 ${issueCount} · 优势 ${goodCount}</p>
          </button>
        `;
      }).join("");

      $("#annotationList").innerHTML = session.annotations.map(annotation => `
        <button type="button" class="annotation-item${annotation.id === state.activeAnnotationId ? " active" : ""}" data-annotation-id="${annotation.id}">
          <div class="annotation-top">
            <span class="annotation-time">${formatClock(annotation.time)}</span>
            <span class="annotation-type ${annotation.type}">${annotationTypes[annotation.type]}</span>
          </div>
          <strong>${annotation.title}</strong>
          <p>${annotation.desc}</p>
        </button>
      `).join("");

      $("#playerMarkers").innerHTML = session.annotations.map(annotation => `
        <button type="button" class="player-marker ${annotation.type}" data-marker-id="${annotation.id}" style="left:${(annotation.time / session.durationSeconds * 100).toFixed(3)}%" title="${formatClock(annotation.time)} ${annotation.title}"></button>
      `).join("");

      $("#reviewSummaryTags").innerHTML = `
        <span class="advantage">优势 ${advantages}</span>
        <span class="problem">问题 ${problems}</span>
        <span class="neutral">标注 ${session.annotations.length}</span>
      `;
      $("#reviewVerdict").textContent = problems > advantages ? "需优化" : (problems >= 2 ? "可复盘" : "表现良好");
      $("#reviewSummaryText").textContent = session.summary;

      if (activeAnnotation) {
        $("#playerAnnotationOverlay").hidden = false;
        $("#playerAnnotationOverlay").innerHTML = `
          <span>${annotationTypes[activeAnnotation.type]} · ${formatClock(activeAnnotation.time)}</span>
          <strong>${activeAnnotation.title}</strong>
        `;
      } else {
        $("#playerAnnotationOverlay").hidden = true;
      }
      updatePlayerFrame();
      renderReviewChart(session);
    }

    function updatePlayerFrame() {
      const session = getSelectedSession();
      if (!session) return;
      const percentage = session.durationSeconds ? state.playerTime / session.durationSeconds * 100 : 0;
      $("#playerProgressFill").style.width = `${clamp(percentage, 0, 100)}%`;
      $("#playerTime").textContent = `${formatClock(state.playerTime)} / ${formatClock(session.durationSeconds)}`;
      $("#playerStageTime").textContent = formatClock(state.playerTime);
      $("#playerBigIcon").textContent = state.playerPlaying ? "❚❚" : "▶";
      $("#playerPlayBtn").textContent = state.playerPlaying ? "暂停" : "播放";
      $("#playerSpeed").textContent = `${state.playerSpeed.toFixed(1)}×`;
    }

    function seekPlayback(time, annotationId = null) {
      const session = getSelectedSession();
      if (!session) return;
      state.playerTime = clamp(time, 0, session.durationSeconds);
      state.playerPlaying = false;
      state.activeAnnotationId = annotationId;
      renderPlayback();
    }

    function renderReviewPage() {
      ensureReviewState();
      const monitor = LIVE_MONITORS[ACTIVE_ACCOUNT.id];
      const liveChip = $("#reviewLiveChip");
      liveChip.className = `live-chip${monitor.live ? "" : " offline"}`;
      liveChip.innerHTML = `<i></i>${monitor.live ? "直播监控中" : "未开播"}`;
      $$(".review-tab").forEach(button => {
        const active = button.dataset.reviewTab === state.reviewTab;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
      });
      $$("[data-review-panel]").forEach(panel => {
        panel.hidden = panel.dataset.reviewPanel !== state.reviewTab;
      });
      renderMonitor(monitor);
      renderPlayback();
      renderAnchorPage();
      updateRecordStatus();
    }

    function renderPageHeader(rows) {
      const scopeText = state.scope === "total" ? "总看板" : "当前账号";
      const subject = state.scope === "total" ? `${ACCOUNTS.length} 个账号` : ACTIVE_ACCOUNT.name;
      $("#pageSub").textContent = `${scopeText} · ${subject} · ${ACTIVE_ACCOUNT.source} · ${formatDate(state.start)} — ${formatDate(state.end)} · ${rows.length} 天`;
      $("#scopeBadge").textContent = state.scope === "total" ? "总看板" : "单账号";
    }

    function renderAccountChrome() {
      $("#accountAvatar").textContent = ACTIVE_ACCOUNT.avatar;
      $("#accountName").textContent = ACTIVE_ACCOUNT.name;

      const live = $("#accountLive");
      const isLive = ACTIVE_ACCOUNT.status === "直播中";
      live.className = `account-live${isLive ? "" : " offline"}`;
      live.innerHTML = `<i></i>${ACTIVE_ACCOUNT.status}`;

      $("#accountOptions").innerHTML = ACCOUNTS.map(account => `
        <button type="button" class="account-option${account.id === state.accountId ? " active" : ""}" data-account-id="${account.id}" role="option" aria-selected="${account.id === state.accountId}">
          <span class="account-avatar">${account.avatar}</span>
          <span class="account-option-main">
            <strong>${account.name}</strong>
            <span>${account.handle} · ${account.qianchuanId}</span>
          </span>
          <span class="account-option-status${account.status === "直播中" ? "" : " offline"}">${account.status}</span>
          <span class="account-option-check">✓</span>
        </button>
      `).join("");

      const scopeLabel = state.scope === "total" ? "总看板" : "当前账号";
      $$("[data-account-label]").forEach(node => { node.textContent = ACTIVE_ACCOUNT.name; });
      $$("[data-account-handle]").forEach(node => { node.textContent = ACTIVE_ACCOUNT.handle; });
      $$("[data-qianchuan-id]").forEach(node => { node.textContent = ACTIVE_ACCOUNT.qianchuanId; });
      $$("[data-scope-label]").forEach(node => { node.textContent = scopeLabel; });

      $$(".scope-switch button").forEach(button => {
        button.classList.toggle("active", button.dataset.scope === state.scope);
      });
    }

    function renderAccountPanel(rows, previousRows) {
      const totalSpend = sum(rows, "spend");
      const accountStats = ACCOUNTS.map(account => {
        const accountRows = getRange(state.start, state.end, account.data);
        const spend = sum(accountRows, "spend");
        const gmv = sum(accountRows, "gmv");
        const orders = sum(accountRows, "orders");
        return {
          account,
          spend,
          gmv,
          orders,
          roi: spend ? gmv / spend : NaN,
          cost: orders ? spend / orders : NaN,
          share: totalSpend ? spend / totalSpend * 100 : 0
        };
      });

      if (state.scope === "total") {
        const syncedCount = ACCOUNTS.filter(account => account.status === "数据已同步").length;
        const validated = Math.abs(accountStats.reduce((total, item) => total + item.spend, 0) - totalSpend) < 1;
        $("#rollupTitle").textContent = "账号汇总";
        $("#rollupBadge").textContent = `${ACCOUNTS.length} 个账号`;
        $("#rollupOverview").innerHTML = `
          <div class="rollup-stat"><span>覆盖账号</span><strong>${ACCOUNTS.length}</strong></div>
          <div class="rollup-stat"><span>已同步</span><strong>${syncedCount}</strong></div>
          <div class="rollup-stat"><span>汇总消耗</span><strong>${formatMetric(totalSpend, "spend", true)}</strong></div>
        `;
        $("#accountList").innerHTML = accountStats.map(item => `
          <button type="button" class="account-row${item.account.id === state.accountId ? " current" : ""}" data-account-id="${item.account.id}">
            <span class="account-row-avatar">${item.account.avatar}</span>
            <span class="account-row-main">
              <span class="account-row-name">${item.account.name}</span>
              <span class="account-row-sub">${item.account.handle} · ${item.account.status}</span>
              <span class="share-track"><span class="share-fill" style="width:${Math.max(2, item.share).toFixed(1)}%; background:${item.account.color}"></span></span>
            </span>
            <span class="account-row-metric">
              <strong>${formatMetric(item.spend, "spend", true)}</strong>
              <span>ROI ${formatNumber(item.roi, 2)}</span>
            </span>
          </button>
        `).join("") + `<div class="rollup-note">按日汇总各账号原始消耗、成交金额与成交订单，再重新计算 ROI 和订单成本，不对账号指标做简单平均。</div>`;
        $("#rollupFoot").innerHTML = `
          <span>汇总 = 各账号数据求和</span>
          <span>${validated ? "<strong>校验通过</strong>" : "<strong style=\"color:var(--danger)\">校验异常</strong>"}</span>
        `;
        return;
      }

      const current = accountStats.find(item => item.account.id === ACTIVE_ACCOUNT.id);
      $("#rollupTitle").textContent = "当前账号";
      $("#rollupBadge").textContent = "单账号";
      $("#rollupOverview").innerHTML = `
        <div class="rollup-stat"><span>成交金额</span><strong>${formatMetric(current.gmv, "gmv", true)}</strong></div>
        <div class="rollup-stat"><span>ROI</span><strong>${formatNumber(current.roi, 2)}</strong></div>
        <div class="rollup-stat"><span>订单成本</span><strong>${formatNumber(current.cost, 1)}</strong></div>
      `;
      $("#accountList").innerHTML = `
        <div class="account-detail-list">
          <div class="account-detail-row"><span>开播账号</span><strong>${ACTIVE_ACCOUNT.name}</strong></div>
          <div class="account-detail-row"><span>抖音号</span><strong>${ACTIVE_ACCOUNT.handle}</strong></div>
          <div class="account-detail-row"><span>千川账户</span><strong>${ACTIVE_ACCOUNT.qianchuanId}</strong></div>
          <div class="account-detail-row"><span>数据状态</span><strong>${ACTIVE_ACCOUNT.status}</strong></div>
          <div class="account-detail-row"><span>数据来源</span><strong>${ACTIVE_ACCOUNT.source}</strong></div>
          <div class="account-detail-row"><span>数据日期</span><strong>${formatDate(state.start)} — ${formatDate(state.end)}</strong></div>
        </div>
        <button type="button" class="account-panel-action" data-action="show-total">查看总看板</button>
      `;
      $("#rollupFoot").innerHTML = `
        <span>全部指标仅归属当前抖音号</span>
        <span><strong>绑定正常</strong></span>
      `;
    }

    function svgElement(tag, attributes = {}) {
      const node = document.createElementNS(svgNS, tag);
      Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
      return node;
    }

    function renderChart(rows, previousRows) {
      const svg = $("#trendChart");
      const wrap = $("#chartWrap");
      const tooltip = $("#chartTooltip");
      svg.replaceChildren();
      tooltip.hidden = true;
      $("#chartEmpty").hidden = rows.length > 0;
      chartGeometry = null;
      if (!rows.length) {
        $("#chartMetaText").textContent = "—";
        $("#previousLegend").hidden = true;
        return;
      }

      const metricKey = state.chartMetric;
      const metric = METRICS[metricKey];
      const currentValues = rows.map(metric.daily);
      const previousValues = previousRows.length === rows.length ? previousRows.map(metric.daily) : [];
      const width = Math.max(480, wrap.clientWidth);
      const height = Math.max(250, wrap.clientHeight || 318);
      const margin = { top: 26, right: 18, bottom: 33, left: 55 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const allValues = currentValues.concat(previousValues).filter(Number.isFinite);
      let min = Math.min(...allValues);
      let max = Math.max(...allValues);
      const padding = (max - min || Math.max(max * 0.08, 1)) * 0.16;
      min = Math.max(0, min - padding);
      max += padding;

      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      svg.setAttribute("aria-label", `${metric.label}趋势图，${formatDate(state.start)}至${formatDate(state.end)}`);

      const xFor = index => margin.left + (rows.length === 1 ? innerWidth / 2 : index / (rows.length - 1) * innerWidth);
      const yFor = value => margin.top + (max - value) / (max - min) * innerHeight;

      const defs = svgElement("defs");
      const gradient = svgElement("linearGradient", { id: "chartAreaGradient", x1: "0", y1: "0", x2: "0", y2: "1" });
      const stopTop = svgElement("stop", { offset: "0%", "stop-color": metric.color, "stop-opacity": "0.18" });
      const stopBottom = svgElement("stop", { offset: "100%", "stop-color": metric.color, "stop-opacity": "0" });
      gradient.append(stopTop, stopBottom);
      defs.appendChild(gradient);
      svg.appendChild(defs);

      if (rows.length >= 7) {
        const bandStart = xFor(Math.max(0, rows.length - 3)) - Math.min(14, innerWidth / Math.max(rows.length, 1) / 2);
        const bandEnd = margin.left + innerWidth;
        svg.appendChild(svgElement("rect", {
          x: bandStart,
          y: margin.top - 7,
          width: Math.max(0, bandEnd - bandStart),
          height: innerHeight + 7,
          rx: 7,
          fill: "#c9723c",
          opacity: "0.045"
        }));
        const bandLabel = svgElement("text", {
          x: bandEnd,
          y: margin.top - 12,
          "text-anchor": "end",
          fill: "#b47b55",
          "font-size": "9",
          "font-weight": "650"
        });
        bandLabel.textContent = "诊断窗口";
        svg.appendChild(bandLabel);
      }

      for (let index = 0; index <= 4; index += 1) {
        const y = margin.top + innerHeight / 4 * index;
        const value = max - (max - min) / 4 * index;
        svg.appendChild(svgElement("line", {
          x1: margin.left,
          y1: y,
          x2: width - margin.right,
          y2: y,
          stroke: "#e8ece7",
          "stroke-width": "1",
          "stroke-dasharray": index === 4 ? "0" : "2 4"
        }));
        const label = svgElement("text", {
          x: margin.left - 9,
          y: y + 3.5,
          "text-anchor": "end",
          fill: "#8a978f",
          "font-size": "9.5",
          "font-variant-numeric": "tabular-nums"
        });
        label.textContent = formatAxisValue(value, metricKey);
        svg.appendChild(label);
      }

      const xLabelCount = Math.min(rows.length, width < 620 ? 4 : 7);
      const labelIndexes = new Set();
      for (let index = 0; index < xLabelCount; index += 1) {
        labelIndexes.add(Math.round(index / Math.max(1, xLabelCount - 1) * (rows.length - 1)));
      }
      labelIndexes.add(rows.length - 1);
      labelIndexes.forEach((index, order) => {
        const label = svgElement("text", {
          x: xFor(index),
          y: height - 10,
          "text-anchor": order === 0 ? "start" : index === rows.length - 1 ? "end" : "middle",
          fill: "#8a978f",
          "font-size": "9.5"
        });
        label.textContent = formatShortDate(rows[index].date);
        svg.appendChild(label);
      });

      if (previousValues.length) {
        const previousPath = previousValues.map((value, index) =>
          `${index ? "L" : "M"}${xFor(index).toFixed(2)},${yFor(value).toFixed(2)}`
        ).join(" ");
        svg.appendChild(svgElement("path", {
          d: previousPath,
          fill: "none",
          stroke: "#aab5ad",
          "stroke-width": "1.3",
          "stroke-dasharray": "4 4",
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
          opacity: "0.85"
        }));
      }

      const currentPath = currentValues.map((value, index) =>
        `${index ? "L" : "M"}${xFor(index).toFixed(2)},${yFor(value).toFixed(2)}`
      ).join(" ");
      const areaPath = `${currentPath} L${xFor(rows.length - 1).toFixed(2)},${margin.top + innerHeight} L${xFor(0).toFixed(2)},${margin.top + innerHeight} Z`;
      svg.appendChild(svgElement("path", { d: areaPath, fill: "url(#chartAreaGradient)" }));
      svg.appendChild(svgElement("path", {
        d: currentPath,
        fill: "none",
        stroke: metric.color,
        "stroke-width": "2.2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      }));

      currentValues.forEach((value, index) => {
        if (index < rows.length - 3 && index !== rows.length - 1) return;
        svg.appendChild(svgElement("circle", {
          cx: xFor(index),
          cy: yFor(value),
          r: index === rows.length - 1 ? "3.4" : "2.4",
          fill: "#fff",
          stroke: metric.color,
          "stroke-width": "1.8"
        }));
      });

      const hoverLine = svgElement("line", {
        x1: 0,
        y1: margin.top,
        x2: 0,
        y2: margin.top + innerHeight,
        stroke: "#8ca097",
        "stroke-width": "1",
        "stroke-dasharray": "3 3",
        opacity: "0"
      });
      const hoverDot = svgElement("circle", {
        cx: 0,
        cy: 0,
        r: "4.2",
        fill: metric.color,
        stroke: "#fff",
        "stroke-width": "2",
        opacity: "0"
      });
      svg.append(hoverLine, hoverDot);

      chartGeometry = {
        rows,
        previousRows,
        metricKey,
        currentValues,
        previousValues,
        width,
        height,
        margin,
        innerWidth,
        xFor,
        yFor,
        hoverLine,
        hoverDot,
        tooltip
      };

      const total = metric.aggregate(rows);
      const previousTotal = previousRows.length ? metric.aggregate(previousRows) : NaN;
      const previousText = Number.isFinite(previousTotal)
        ? `上期 ${formatMetric(previousTotal, metricKey, true)}`
        : "无上期对比";
      $("#chartMetaText").innerHTML = `本期 <strong>${formatMetric(total, metricKey, true)}</strong> · ${previousText}`;
      $("#previousLegend").hidden = previousValues.length === 0;
    }

    function formatAxisValue(value, metricKey) {
      const metric = METRICS[metricKey];
      if (metric.kind === "percent") return `${value.toFixed(1)}%`;
      if (metric.kind === "currency") {
        if (value >= 10000) return `¥${(value / 10000).toFixed(1)}万`;
        return `¥${Math.round(value)}`;
      }
      return value.toFixed(metricKey === "roi" ? 1 : 0);
    }

    function handleChartPointer(event) {
      if (!chartGeometry) return;
      const geometry = chartGeometry;
      const svg = $("#trendChart");
      const rect = svg.getBoundingClientRect();
      const pointerX = (event.clientX - rect.left) * (geometry.width / rect.width);
      const ratio = clamp((pointerX - geometry.margin.left) / geometry.innerWidth, 0, 1);
      const index = Math.round(ratio * Math.max(0, geometry.rows.length - 1));
      const row = geometry.rows[index];
      const value = geometry.currentValues[index];
      const x = geometry.xFor(index);
      const y = geometry.yFor(value);
      const metric = METRICS[geometry.metricKey];
      const tooltip = geometry.tooltip;

      geometry.hoverLine.setAttribute("x1", x);
      geometry.hoverLine.setAttribute("x2", x);
      geometry.hoverLine.setAttribute("opacity", "1");
      geometry.hoverDot.setAttribute("cx", x);
      geometry.hoverDot.setAttribute("cy", y);
      geometry.hoverDot.setAttribute("opacity", "1");

      const previousValue = geometry.previousValues[index];
      const previousRow = geometry.previousRows[index];
      tooltip.innerHTML = `
        <div class="tooltip-date">${formatDate(row.date)}</div>
        <div class="tooltip-row"><span><i></i>本期${metric.short}</span><strong>${formatMetric(value, geometry.metricKey)}</strong></div>
        ${Number.isFinite(previousValue) ? `<div class="tooltip-row previous"><span><i></i>上期${metric.short}</span><strong>${formatMetric(previousValue, geometry.metricKey)}</strong></div><div class="tooltip-date" style="margin:6px 0 0">${formatDate(previousRow.date)}</div>` : ""}
      `;
      tooltip.hidden = false;
      const pixelX = x / geometry.width * rect.width;
      const pixelY = y / geometry.height * rect.height;
      const halfTooltip = 82;
      tooltip.style.left = `${clamp(pixelX, halfTooltip, rect.width - halfTooltip)}px`;
      tooltip.style.top = `${Math.max(pixelY, 66)}px`;
    }

    function clearChartPointer() {
      if (!chartGeometry) return;
      chartGeometry.hoverLine.setAttribute("opacity", "0");
      chartGeometry.hoverDot.setAttribute("opacity", "0");
      chartGeometry.tooltip.hidden = true;
    }

    function getDiagSeries(accountId) {
      if (DIAG_SERIES[accountId]) return DIAG_SERIES[accountId];
      const profile = DIAG_LIVE[accountId];
      const riskSet = new Set([172, 193, 224, 300, 334, 352]);
      const series = [];
      for (let index = 0; index < 360; index += 1) {
        const anchor = clamp(profile.base.anchor + Math.sin(index / 12) * 8 + Math.cos(index / 31) * 5, 20, 98);
        const user = clamp(profile.base.user + Math.sin(index / 15 + 1) * 9 + Math.cos(index / 24) * 4, 20, 98);
        const goods = clamp(profile.base.goods + Math.sin(index / 18 + 2) * 7 + Math.cos(index / 29) * 4, 20, 98);
        const risk = riskSet.has(index);
        const riskPhrase = risk ? profile.riskPhrases[index % profile.riskPhrases.length] : "";
        series.push({
          t: DIAG_BASE_SECONDS + index * 5,
          anchor,
          user,
          goods,
          risk,
          riskPhrase,
          watchRate: Math.max(1, profile.user.watchRate + Math.sin(index / 13) * 2.6 + Math.cos(index / 27) * 1.2),
          productClicks: Math.max(1, Math.round(profile.user.productClicks + Math.sin(index / 17 + 1) * 90 + Math.cos(index / 9) * 40)),
          productClickRate: Math.max(0.5, profile.user.productClickRate + Math.sin(index / 16 + 1) * 1.2),
          dwell: Math.max(5, profile.user.dwell + Math.sin(index / 20) * 5.5 + Math.cos(index / 33) * 2),
          online: Math.max(1, Math.round(profile.user.online + Math.sin(index / 11) * 800 + Math.cos(index / 19) * 300)),
          comments: Math.max(1, Math.round(profile.user.comments + Math.sin(index / 8) * 40))
        });
      }
      DIAG_SERIES[accountId] = series;
      return series;
    }

    function appendDiagPoint(accountId) {
      const profile = DIAG_LIVE[accountId];
      const series = getDiagSeries(accountId);
      const last = series[series.length - 1];
      const tick = Math.round(last.t / 5);
      const risk = tick % 61 === 0;
      const point = {
        t: last.t + 5,
        anchor: clamp(last.anchor + Math.sin(tick / 4) * 2.2 - (last.anchor - profile.base.anchor) * 0.1, 20, 98),
        user: clamp(last.user + Math.sin(tick / 5 + 1) * 2.8 - (last.user - profile.base.user) * 0.1, 20, 98),
        goods: clamp(last.goods + Math.cos(tick / 6) * 2.5 - (last.goods - profile.base.goods) * 0.1, 20, 98),
        risk,
        riskPhrase: risk ? profile.riskPhrases[tick % profile.riskPhrases.length] : "",
        watchRate: clamp(last.watchRate + Math.sin(tick / 6) * 0.28 - (last.watchRate - profile.user.watchRate) * 0.05, 1, 60),
        productClicks: Math.max(1, Math.round(last.productClicks + Math.sin(tick / 5) * 28 - (last.productClicks - profile.user.productClicks) * 0.08)),
        productClickRate: clamp(last.productClickRate + Math.sin(tick / 7) * 0.16 - (last.productClickRate - profile.user.productClickRate) * 0.06, 0.5, 30),
        dwell: clamp(last.dwell + Math.cos(tick / 8) * 0.6 - (last.dwell - profile.user.dwell) * 0.06, 5, 120),
        online: Math.max(1, Math.round(last.online + Math.sin(tick / 4) * 120 - (last.online - profile.user.online) * 0.06)),
        comments: Math.max(1, Math.round(last.comments + Math.cos(tick / 5) * 12 - (last.comments - profile.user.comments) * 0.06))
      };
      series.push(point);
      if (series.length > 360) series.shift();
      return point;
    }

    function renderLiveDiagnosis() {
      const profile = DIAG_LIVE[ACTIVE_ACCOUNT.id];
      if (!profile) return;
      const series = getDiagSeries(ACTIVE_ACCOUNT.id);
      const latest = series[series.length - 1];
      const live = profile.live;
      const capturing = live && state.diagCapturing;
      const userTone = latest.watchRate >= 15 && latest.dwell >= 30 ? "good" : "warn";
      const goodsTone = latest.goods >= 60 && profile.goods.stock > 0 ? "good" : "warn";
      const anchorTone = latest.anchor >= 65 ? "good" : latest.anchor >= 50 ? "warn" : "bad";

      const liveChip = $("#diagLiveChip");
      liveChip.className = `live-chip${live ? "" : " offline"}`;
      liveChip.innerHTML = `<i></i>${live ? (capturing ? "实时诊断中" : "诊断已暂停") : "未开播"}`;
      const captureButton = $("#diagCaptureToggle");
      captureButton.disabled = !live;
      captureButton.textContent = !live ? "未开播" : capturing ? "暂停捕捉" : "开始捕捉";
      $("#diagCaptureLabel").textContent = capturing ? "捕捉中" : "已暂停";
      $(".diag-live-dot").classList.toggle("paused", !capturing);

      $("#diagAnchorName").textContent = `${profile.anchorName} · ${ANCHOR_PROFILES[ACTIVE_ACCOUNT.id].anchorId}`;
      $("#diagAnchorBadge").textContent = profile.anchorBadge;
      $("#diagAnchorBadge").className = `diag-status ${profile.anchorTone}`;
      $("#diagAnchorState").innerHTML = profile.anchorMetrics.map(item => `
        <div class="diag-anchor-metric"><span>${item.label}</span><strong>${item.value}</strong><em>${item.note}</em></div>
      `).join("");

      const badScripts = profile.scriptIssues.filter(item => item.level === "bad").length;
      $("#diagScriptBadge").textContent = badScripts ? `${badScripts} 条高风险` : `${profile.scriptIssues.length} 条提醒`;
      $("#diagScriptBadge").className = `diag-status ${badScripts ? "bad" : "warn"}`;
      $("#diagScriptIssues").innerHTML = profile.scriptIssues.map(issue => `
        <div class="diag-script-item">
          <div class="diag-script-top">
            <span class="diag-script-time">${issue.time}</span>
            <span class="diag-script-type ${issue.level === "warn" ? "warn" : ""}">${issue.type}</span>
          </div>
          <strong>检测到「${issue.phrase}」</strong>
          <p>${issue.note}</p>
        </div>
      `).join("");

      $("#diagUserBadge").textContent = userTone === "good" ? "平稳" : "需关注";
      $("#diagUserBadge").className = `diag-status ${userTone}`;
      $("#diagUserState").innerHTML = [
        ["看播率", `${latest.watchRate.toFixed(1)}%`, "实时反馈"],
        ["商品点击", formatNumber(latest.productClicks, 0), `点击率 ${latest.productClickRate.toFixed(1)}%`],
        ["停留时长", `${latest.dwell.toFixed(1)}s`, "平均停留"],
        ["在线人数", formatNumber(latest.online, 0), `评论 ${formatNumber(latest.comments, 0)}/分钟`]
      ].map(([label, value, note]) => `
        <div class="diag-user-metric"><span>${label}</span><strong>${value}</strong><em>${note}</em></div>
      `).join("");

      $("#diagGoodsBadge").textContent = goodsTone === "good" ? "正常" : "承压";
      $("#diagGoodsBadge").className = `diag-status ${goodsTone}`;
      $("#diagGoodsState").innerHTML = [
        ["当前商品", profile.goods.product],
        ["库存", `${profile.goods.stock} 件`],
        ["商品点击率", `${latest.productClickRate.toFixed(1)}%`],
        ["转化率", `${profile.goods.conversion.toFixed(2)}%`],
        ["场景", profile.goods.scene],
        ["互动氛围", profile.goods.interaction]
      ].map(([label, value]) => `
        <div class="diag-goods-row"><span>${label}</span><strong>${value}</strong></div>
      `).join("");

      $("#diagCenterKpis").innerHTML = [
        ["主播状态", Math.round(latest.anchor), profile.anchorBadge],
        ["用户状态", Math.round(latest.user), userTone === "good" ? "平稳" : "需关注"],
        ["货场承接", Math.round(latest.goods), goodsTone === "good" ? "正常" : "承压"],
        ["话术风险", profile.scriptIssues.length, "条"]
      ].map(([label, value, note]) => `
        <div class="diag-kpi"><span>${label}</span><strong>${value}</strong><em>${note}</em></div>
      `).join("");

      $("#diagLiveTime").textContent = formatClock(latest.t);
      $("#diagStageAnchor").textContent = `状态${profile.anchorBadge}`;
      $("#diagStageAnchorNote").textContent = `${profile.anchorName} · 语速 ${profile.anchorMetrics[0].value}`;
      $("#diagStageGoods").textContent = profile.goods.product;
      $("#diagStageGoodsNote").textContent = `库存 ${profile.goods.stock} · 点击率 ${latest.productClickRate.toFixed(1)}%`;
      $("#diagStageScene").textContent = profile.goods.scene;
      $("#diagStageSceneNote").textContent = `互动 ${profile.goods.interaction}`;
      $("#diagStageStatus").textContent = !live ? "等待开播" : capturing ? "实时捕捉中" : "捕捉已暂停";

      $$("#diagWindowTabs button").forEach(button => {
        button.classList.toggle("active", Number(button.dataset.diagWindow) === state.diagWindow);
      });
      $("#diagnosisNavAlert").hidden = !(live && (badScripts > 0 || userTone === "warn" || latest.anchor < 55 || latest.goods < 55));
      renderDiagChart(series, profile);
    }

    function renderDiagChart(series, profile) {
      const pointsToShow = Math.max(12, Math.round(state.diagWindow * 60 / 5));
      const points = series.slice(-pointsToShow);
      const svg = $("#diagChart");
      const wrap = $("#diagChartWrap");
      const tooltip = $("#diagChartTooltip");
      svg.replaceChildren();
      tooltip.hidden = true;
      diagChartGeometry = null;
      if (!points.length) return;

      const width = Math.max(320, wrap.clientWidth || 640);
      const height = Math.max(240, wrap.clientHeight || 288);
      const margin = { top: 18, right: 18, bottom: 30, left: 38 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const xFor = index => margin.left + (points.length === 1 ? innerWidth / 2 : index / (points.length - 1) * innerWidth);
      const yFor = value => margin.top + (100 - value) / 100 * innerHeight;
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

      for (let index = 0; index <= 4; index += 1) {
        const y = margin.top + innerHeight / 4 * index;
        const value = 100 - index * 25;
        svg.appendChild(svgElement("line", {
          x1: margin.left, y1: y, x2: width - margin.right, y2: y,
          stroke: "#e8ece7", "stroke-width": "1", "stroke-dasharray": index === 4 ? "0" : "2 4"
        }));
        const label = svgElement("text", {
          x: margin.left - 8, y: y + 3.5, "text-anchor": "end",
          fill: "#8a978f", "font-size": "9", "font-variant-numeric": "tabular-nums"
        });
        label.textContent = String(value);
        svg.appendChild(label);
      }

      const labelCount = Math.min(points.length, width < 700 ? 4 : 6);
      const labelIndexes = new Set();
      for (let index = 0; index < labelCount; index += 1) {
        labelIndexes.add(Math.round(index / Math.max(1, labelCount - 1) * (points.length - 1)));
      }
      labelIndexes.add(points.length - 1);
      labelIndexes.forEach((index, order) => {
        const label = svgElement("text", {
          x: xFor(index), y: height - 9,
          "text-anchor": order === 0 ? "start" : index === points.length - 1 ? "end" : "middle",
          fill: "#8a978f", "font-size": "9"
        });
        label.textContent = formatClockShort(points[index].t);
        svg.appendChild(label);
      });

      const pathFor = key => points.map((point, index) =>
        `${index ? "L" : "M"}${xFor(index).toFixed(1)},${yFor(point[key]).toFixed(1)}`
      ).join(" ");
      svg.appendChild(svgElement("path", { d: pathFor("anchor"), fill: "none", stroke: "#0b7a58", "stroke-width": "2.1", "stroke-linecap": "round", "stroke-linejoin": "round" }));
      svg.appendChild(svgElement("path", { d: pathFor("user"), fill: "none", stroke: "#2b6f94", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round" }));
      svg.appendChild(svgElement("path", { d: pathFor("goods"), fill: "none", stroke: "#c9723c", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round" }));

      points.forEach((point, index) => {
        if (!point.risk) return;
        svg.appendChild(svgElement("circle", {
          cx: xFor(index), cy: height - 13, r: "3.4",
          fill: "#c9723c", stroke: "#fff", "stroke-width": "1.5"
        }));
      });

      const hoverLine = svgElement("line", {
        x1: 0, y1: margin.top, x2: 0, y2: margin.top + innerHeight,
        stroke: "#8ca097", "stroke-width": "1", "stroke-dasharray": "3 3", opacity: "0"
      });
      const hoverDot = svgElement("circle", {
        cx: 0, cy: 0, r: "4.2", fill: "#0b7a58", stroke: "#fff", "stroke-width": "2", opacity: "0"
      });
      svg.append(hoverLine, hoverDot);

      const riskPoints = points.map((point, index) => ({ point, index })).filter(item => item.point.risk);
      const railScale = (wrap.clientWidth || width) / width;
      $("#diagPointRail").innerHTML = riskPoints.map(item => `
        <button type="button" class="review-point problem" style="left:${(xFor(item.index) * railScale).toFixed(1)}px" data-diag-risk-index="${item.index}" title="${formatClock(item.point.t)} 话术风险">
          <span class="review-point-dot"></span>
          <span class="review-point-time">${formatClockShort(item.point.t)}</span>
        </button>
      `).join("");
      $$("#diagPointRail [data-diag-risk-index]").forEach(button => {
        const index = Number(button.dataset.diagRiskIndex);
        const show = () => showDiagChartTooltip(points[index], index, button);
        button.addEventListener("pointerenter", show);
        button.addEventListener("focus", show);
        button.addEventListener("click", show);
        button.addEventListener("pointerleave", hideDiagChartTooltip);
        button.addEventListener("blur", hideDiagChartTooltip);
      });

      $("#diagChartMeta").textContent = `近 ${state.diagWindow} 分钟 · ${points.length} 个捕捉点 · ${riskPoints.length} 条话术风险`;
      diagChartGeometry = { points, width, height, margin, innerWidth, xFor, yFor, hoverLine, hoverDot, profile };
    }

    function showDiagChartTooltip(point, index, sourceElement = null) {
      if (!diagChartGeometry) return;
      const tooltip = $("#diagChartTooltip");
      const panel = $(".live-diag-chart-panel");
      const wrap = $("#diagChartWrap");
      const geometry = diagChartGeometry;
      const profile = geometry.profile;
      const anchorLabel = point.anchor >= 70 ? "状态良好" : point.anchor >= 55 ? "状态一般" : "需关注";
      const userLabel = point.user >= 65 ? "平稳" : point.user >= 50 ? "一般" : "需关注";
      const goodsLabel = point.goods >= 65 ? "承接正常" : point.goods >= 50 ? "承压" : "需调整";

      tooltip.innerHTML = `
        <div class="review-tooltip-head"><span>${formatClock(point.t)}</span><span>实时捕捉</span></div>
        <div class="review-tooltip-tags">
          <span class="review-tooltip-tag ${point.anchor >= 65 ? "good" : "bad"}">人 · ${anchorLabel}</span>
          <span class="review-tooltip-tag ${point.risk ? "bad" : "neutral"}">${point.risk ? "话术风险" : "话术合规"}</span>
          <span class="review-tooltip-tag ${point.user >= 60 ? "good" : "bad"}">用户 · ${userLabel}</span>
          <span class="review-tooltip-tag ${point.goods >= 60 ? "good" : "bad"}">货场 · ${goodsLabel}</span>
        </div>
        <div class="review-tooltip-grid">
          <div><span>主播状态</span><strong>${Math.round(point.anchor)}</strong></div>
          <div><span>用户状态</span><strong>${Math.round(point.user)}</strong></div>
          <div><span>货场承接</span><strong>${Math.round(point.goods)}</strong></div>
        </div>
        <div class="review-tooltip-note"><span>用户状态</span><p>看播率 ${point.watchRate.toFixed(1)}% · 商品点击 ${formatNumber(point.productClicks, 0)} 次（${point.productClickRate.toFixed(1)}%）· 停留 ${point.dwell.toFixed(1)}s</p></div>
        <div class="review-tooltip-note"><span>货场状态</span><p>${profile.goods.product} · 库存 ${profile.goods.stock} · ${profile.goods.scene}</p></div>
        <div class="review-tooltip-note"><span>话术状态</span><p>${point.risk ? `检测到「${point.riskPhrase}」，建议立即调整表达。` : "未检测到违禁话术（示例词库）。"}</p></div>
      `;

      const panelRect = panel.getBoundingClientRect();
      const wrapRect = wrap.getBoundingClientRect();
      let left;
      let top;
      if (sourceElement) {
        const sourceRect = sourceElement.getBoundingClientRect();
        left = sourceRect.left - panelRect.left + sourceRect.width / 2;
        top = sourceRect.bottom - panelRect.top;
      } else {
        const x = geometry.xFor(index) / geometry.width * wrapRect.width;
        left = wrapRect.left - panelRect.left + x;
        top = wrapRect.bottom - panelRect.top - 4;
      }
      const half = Math.min(165, panelRect.width / 2 - 8);
      tooltip.style.left = `${clamp(left, half, panelRect.width - half)}px`;
      tooltip.style.top = `${Math.max(220, top)}px`;
      tooltip.hidden = false;
    }

    function hideDiagChartTooltip() {
      const tooltip = $("#diagChartTooltip");
      if (tooltip) tooltip.hidden = true;
      if (diagChartGeometry) {
        diagChartGeometry.hoverLine.setAttribute("opacity", "0");
        diagChartGeometry.hoverDot.setAttribute("opacity", "0");
      }
    }

    function handleDiagChartPointer(event) {
      if (!diagChartGeometry) return;
      const geometry = diagChartGeometry;
      const svg = $("#diagChart");
      const rect = svg.getBoundingClientRect();
      const pointerX = (event.clientX - rect.left) * (geometry.width / rect.width);
      const ratio = clamp((pointerX - geometry.margin.left) / geometry.innerWidth, 0, 1);
      const index = Math.round(ratio * Math.max(0, geometry.points.length - 1));
      const point = geometry.points[index];
      const x = geometry.xFor(index);
      const y = geometry.yFor(point.anchor);
      geometry.hoverLine.setAttribute("x1", x);
      geometry.hoverLine.setAttribute("x2", x);
      geometry.hoverLine.setAttribute("opacity", "1");
      geometry.hoverDot.setAttribute("cx", x);
      geometry.hoverDot.setAttribute("cy", y);
      geometry.hoverDot.setAttribute("opacity", "1");
      showDiagChartTooltip(point, index);
    }

    function handleDiagBannedLibrary(file) {
      if (!file) return;
      file.text().then(text => {
        diagBannedWords = text.split(/\r?\n/).map(word => word.trim()).filter(Boolean);
        $("#diagBannedStatus").textContent = `已载入 ${diagBannedWords.length} 条 · 实时匹配待接入 ASR`;
      }).catch(() => {
        $("#diagBannedStatus").textContent = "词库读取失败，请重试";
      });
    }

    function escapeHTML(value) {
      return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    let toastTimer = null;

    function showToast(message) {
      let toast = $("#appToast");
      if (!toast) {
        toast = document.createElement("div");
        toast.id = "appToast";
        toast.className = "toast";
        toast.setAttribute("role", "status");
        document.body.appendChild(toast);
      }
      toast.textContent = message;
      window.requestAnimationFrame(() => toast.classList.add("show"));
      window.clearTimeout(toastTimer);
      toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2600);
    }

    function copyText(text, successMessage) {
      const fallback = () => {
        const area = document.createElement("textarea");
        area.value = text;
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        try {
          document.execCommand("copy");
          showToast(successMessage);
        } catch (error) {
          showToast("复制失败，请手动选择文本");
        }
        area.remove();
      };
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text).then(() => showToast(successMessage)).catch(fallback);
      } else {
        fallback();
      }
    }

    function formatSigned(value, decimals = 0, suffix = "") {
      if (!Number.isFinite(value)) return "—";
      const sign = value > 0 ? "+" : "";
      return `${sign}${value.toFixed(decimals)}${suffix}`;
    }

    function bannedCategoryLabel(id) {
      return BANNED_CATEGORIES.find(category => category.id === id)?.label || "待分类";
    }

    function normalizeBannedCategory(value) {
      const text = String(value || "").trim();
      if (!text) return "pending";
      const exact = BANNED_CATEGORIES.find(category =>
        category.id === text.toLowerCase() || category.label === text || category.label.includes(text)
      );
      if (exact && exact.id !== "all") return exact.id;
      if (/绝对|极限|排名/.test(text)) return "absolute";
      if (/承诺|保证|永久/.test(text)) return "promise";
      if (/功效|医疗|治疗/.test(text)) return "efficacy";
      if (/价格|促销|诱导/.test(text)) return "price";
      if (/平台|导流|站外/.test(text)) return "platform";
      return "pending";
    }

    function normalizeBannedLevel(value) {
      const text = String(value || "").trim().toLowerCase();
      if (["high", "高", "高风", "高风险"].includes(text)) return "high";
      if (["low", "低", "低风", "低风险"].includes(text)) return "low";
      return "mid";
    }

    function populateScriptSelects() {
      const categoryOptions = BANNED_CATEGORIES.map(category =>
        `<option value="${category.id}">${escapeHTML(category.label)}</option>`
      ).join("");
      const wordCategory = $("#scriptWordCategory");
      if (wordCategory.dataset.ready !== "1") {
        wordCategory.innerHTML = categoryOptions;
        wordCategory.dataset.ready = "1";
      }
      wordCategory.value = state.scriptWordCategory;

      const pasteCategory = $("#scriptPasteCategory");
      if (pasteCategory.dataset.ready !== "1") {
        pasteCategory.innerHTML = BANNED_CATEGORIES.filter(category => category.id !== "all").map(category =>
          `<option value="${category.id}">${escapeHTML(category.label)}</option>`
        ).join("");
        pasteCategory.dataset.ready = "1";
      }

      const scenes = [...new Set(QUALITY_SCRIPTS.map(script => script.scene))];
      const qualityScene = $("#qualityScene");
      if (qualityScene.dataset.ready !== "1") {
        qualityScene.innerHTML = `<option value="all">全部场景</option>${scenes.map(scene =>
          `<option value="${escapeHTML(scene)}">${escapeHTML(scene)}</option>`
        ).join("")}`;
        qualityScene.dataset.ready = "1";
      }
      qualityScene.value = state.scriptQualityScene;

      const lowAnchor = $("#lowAnchor");
      if (lowAnchor.dataset.ready !== "1") {
        lowAnchor.innerHTML = `<option value="all">全部主播</option>${Object.entries(QUALITY_META).map(([id, meta]) =>
          `<option value="${id}">${escapeHTML(meta.name)}</option>`
        ).join("")}`;
        lowAnchor.dataset.ready = "1";
      }
      lowAnchor.value = state.lowAnchor;

      const lowScenes = [...new Set(LOW_SCRIPTS.map(script => script.scene))];
      const lowScene = $("#lowScene");
      if (lowScene.dataset.ready !== "1") {
        lowScene.innerHTML = `<option value="all">全部场景</option>${lowScenes.map(scene =>
          `<option value="${escapeHTML(scene)}">${escapeHTML(scene)}</option>`
        ).join("")}`;
        lowScene.dataset.ready = "1";
      }
      lowScene.value = state.lowScene;
    }

    function renderScriptPage() {
      populateScriptSelects();
      ensureScriptLiveRows();
      renderScriptOverview();
      $$("#scriptTabs button").forEach(button => {
        const active = button.dataset.scriptTab === state.scriptTab;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
      });
      $$("[data-script-panel]").forEach(panel => {
        panel.hidden = panel.dataset.scriptPanel !== state.scriptTab;
      });
      renderBannedLibrary();
      renderQualityScripts();
      renderLowScripts();
      renderScriptLive();
      if (state.scriptTab === "live") {
        window.requestAnimationFrame(renderScriptImpactChart);
      }
    }

    function renderScriptOverview() {
      const liveRows = state.scriptLiveRows.filter(row => row.status === "ready").slice(-6);
      const liveAverage = liveRows.length
        ? liveRows.reduce((total, row) => total + row.score, 0) / liveRows.length
        : 0;
      const lowPending = LOW_SCRIPTS.filter(script => script.status === "待优化").length;
      const isLive = Boolean(DIAG_LIVE[ACTIVE_ACCOUNT.id]?.live);
      $("#scriptOverview").innerHTML = `
        <article class="panel metric-tile">
          <span class="metric-tile-label">违禁词库</span>
          <div class="metric-tile-value">${formatNumber(BANNED_LIBRARY_META.total, 0)}<em>条</em></div>
          <div class="metric-tile-foot">本周新增 <strong>+${BANNED_LIBRARY_META.weeklyNew}</strong> · 高风险 ${BANNED_LIBRARY_META.highRisk} 条</div>
        </article>
        <article class="panel metric-tile">
          <span class="metric-tile-label">主播优质话术</span>
          <div class="metric-tile-value">${QUALITY_SCRIPTS.length}<em>条</em></div>
          <div class="metric-tile-foot">覆盖 <strong>3 位主播</strong> · 合集 ${state.scriptCollection.size} 条</div>
        </article>
        <article class="panel metric-tile">
          <span class="metric-tile-label">持续低效话术</span>
          <div class="metric-tile-value">${LOW_SCRIPTS.length}<em>条</em></div>
          <div class="metric-tile-foot"><strong class="bad">${lowPending} 条待优化</strong> · 每 3 天整理一版</div>
        </article>
        <article class="panel metric-tile">
          <span class="metric-tile-label">实时话术影响</span>
          <div class="metric-tile-value">${liveAverage ? Math.round(liveAverage) : "—"}<em>分</em></div>
          <div class="metric-tile-foot">最近 6 句均值 · 4 秒归因 · <strong>${isLive ? "直播中" : "演示回放"}</strong></div>
        </article>
      `;
      const chip = $("#scriptLiveChip");
      if (chip) {
        chip.className = `live-chip${isLive ? "" : " offline"}`;
        chip.innerHTML = `<i></i>${isLive ? "直播中" : "未开播"}`;
      }
    }

    function renderBannedLibrary() {
      const query = state.scriptWordQuery.trim().toLowerCase();
      const filtered = BANNED_WORDS.filter(item => {
        const matchesCategory = state.scriptWordCategory === "all" || item.categoryId === state.scriptWordCategory;
        if (!matchesCategory) return false;
        if (!query) return true;
        return [item.word, item.note, item.replacement, item.source].some(value =>
          String(value || "").toLowerCase().includes(query)
        );
      });

      $("#scriptWordStats").innerHTML = `
        <span>词库 <strong>${formatNumber(BANNED_LIBRARY_META.total, 0)}</strong> 条</span>
        <span>本周 <strong>+${BANNED_LIBRARY_META.weeklyNew}</strong></span>
        <span>高风险 <strong>${BANNED_LIBRARY_META.highRisk}</strong></span>
        <span>更新于 <strong>${BANNED_LIBRARY_META.updated}</strong></span>
      `;

      $("#scriptWordTableBody").innerHTML = filtered.length ? filtered.map(item => {
        const levelClass = item.level === "high" ? "" : item.level;
        const levelText = item.level === "high" ? "高" : item.level === "mid" ? "中" : "低";
        return `
          <tr>
            <td><span class="word-term ${levelClass}">${escapeHTML(item.word)}</span></td>
            <td>${escapeHTML(bannedCategoryLabel(item.categoryId))}</td>
            <td><span class="mini-tag ${item.level === "high" ? "bad" : item.level === "mid" ? "warn" : "good"}">${levelText}</span></td>
            <td>
              <div>${escapeHTML(item.note)}</div>
              <div class="word-suggestion">${escapeHTML(item.replacement)}</div>
            </td>
            <td>${escapeHTML(item.source)}</td>
            <td>${escapeHTML(item.updated)}</td>
            <td><span class="mini-tag ${item.status === "生效" ? "good" : "warn"}">${escapeHTML(item.status)}</span></td>
          </tr>
        `;
      }).join("") : `
        <tr><td colspan="7" style="padding:28px;text-align:center;color:var(--muted);">没有匹配的词条</td></tr>
      `;
      $("#scriptWordFoot").textContent = `显示 ${filtered.length} / ${formatNumber(BANNED_LIBRARY_META.total, 0)} 条 · 最近更新优先展示`;
      $("#bannedTabCount").textContent = formatNumber(BANNED_LIBRARY_META.total, 0);

      $("#scriptUploadChannels").innerHTML = UPLOAD_CHANNELS.map(channel => `
        <div class="upload-channel">
          <div class="upload-channel-top">
            <strong>${escapeHTML(channel.title)}</strong>
            <span class="mini-tag ${channel.tone}">${escapeHTML(channel.status)}</span>
          </div>
          <p>${escapeHTML(channel.desc)}</p>
          ${channel.action === "local" ? `<button type="button" data-upload-word-local>选择文件</button>` : ""}
        </div>
      `).join("");

      $("#scriptWordVersions").innerHTML = BANNED_VERSIONS.slice(0, 4).map(version => `
        <div class="version-row">
          <strong>${escapeHTML(version.version)}</strong>
          <span>${escapeHTML(version.note)}</span>
          <em>${escapeHTML(version.date)} · ${escapeHTML(version.count)}</em>
        </div>
      `).join("");
    }

    function addBannedWords(entries, sourceLabel) {
      const existingWords = new Set(BANNED_WORDS.map(item => item.word));
      const unique = entries.filter(item => item.word && !existingWords.has(item.word) && existingWords.add(item.word));
      if (!unique.length) {
        showToast("没有新增词条，已自动跳过重复项");
        return;
      }
      BANNED_WORDS.unshift(...unique);
      BANNED_LIBRARY_META.total += unique.length;
      BANNED_LIBRARY_META.weeklyNew += unique.length;
      BANNED_LIBRARY_META.highRisk += unique.filter(item => item.level === "high").length;
      BANNED_LIBRARY_META.updated = "今天";
      const latestVersion = Math.max(...BANNED_VERSIONS.map(version => Number(String(version.version).split(".").pop()) || 0));
      BANNED_VERSIONS.unshift({
        version: `V2.${latestVersion + 1}`,
        date: "今天",
        note: sourceLabel,
        count: `+${unique.length}`
      });
      diagBannedWords = BANNED_WORDS.map(item => item.word);
      renderBannedLibrary();
      renderScriptOverview();
      showToast(`已新增 ${unique.length} 条词条，状态为“待复核”`);
    }

    function handleScriptWordFile(file) {
      if (!file) return;
      if (file.size > 1024 * 1024) {
        showToast("文件超过 1 MB，请拆分后上传");
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const lines = String(reader.result || "").split(/\r?\n/).map(line => line.trim()).filter(Boolean);
        const entries = lines.map((line, index) => {
          const cells = line.split(/[,\t]/).map(cell => cell.trim());
          if (index === 0 && /词条|word|关键词/i.test(cells[0])) return null;
          return {
            id: `upload-${Date.now()}-${index}`,
            word: cells[0],
            categoryId: normalizeBannedCategory(cells[1]),
            level: normalizeBannedLevel(cells[2]),
            note: "本地上传，待人工复核适用范围。",
            replacement: cells[3] || "待补充替换建议",
            source: `本地上传 · ${file.name}`,
            updated: "今天",
            status: "待复核",
            hits: 0
          };
        }).filter(Boolean);
        addBannedWords(entries, `本地上传 ${file.name}`);
      };
      reader.onerror = () => showToast("文件读取失败，请重试");
      reader.readAsText(file, "UTF-8");
    }

    function renderQualityScripts() {
      if (!QUALITY_META[state.scriptQualityAnchor]) state.scriptQualityAnchor = "fashion";
      const meta = QUALITY_META[state.scriptQualityAnchor];
      const scripts = QUALITY_SCRIPTS.filter(script =>
        script.accountId === state.scriptQualityAnchor &&
        (state.scriptQualityScene === "all" || script.scene === state.scriptQualityScene)
      );
      $("#qualityAnchorTabs").innerHTML = Object.entries(QUALITY_META).map(([id, item]) => {
        const active = id === state.scriptQualityAnchor;
        return `
          <button type="button" class="anchor-tab${active ? " active" : ""}" data-quality-anchor="${id}" role="tab" aria-selected="${active}">
            <span class="anchor-tab-avatar">${escapeHTML(item.avatar)}</span>
            <span>${escapeHTML(item.name)}<small> ${escapeHTML(item.anchorId)}</small></span>
          </button>
        `;
      }).join("");
      $("#qualitySessionNote").innerHTML = `
        <strong>${escapeHTML(meta.session)}</strong>
        <span>已摘取 ${meta.extracted} 条</span>
        <span>当前展示 ${scripts.length} 条</span>
        <span>高转化 ${meta.highConversion} 条</span>
        <span>高停留 ${meta.highDwell} 条</span>
        <span>AI 置信度 ${meta.confidence}%</span>
        <span>出单高峰 ${escapeHTML(meta.orderPeak)}</span>
      `;
      $("#qualityScriptGrid").innerHTML = scripts.length ? scripts.map(script => {
        const collected = state.scriptCollection.has(script.id);
        return `
          <article class="quote-card">
            <div class="quote-card-top">
              <span class="mini-tag blue">${escapeHTML(script.scene)}</span>
              <span class="mini-tag good">转化 +${script.lift}%</span>
            </div>
            <blockquote>“${escapeHTML(script.quote)}”</blockquote>
            <div class="quote-stats">
              <div class="quote-stat"><span>转化率</span><strong>${script.conversion.toFixed(1)}%</strong></div>
              <div class="quote-stat"><span>平均停留</span><strong>${script.dwell.toFixed(1)}s</strong></div>
              <div class="quote-stat"><span>使用次数</span><strong>${script.uses}</strong></div>
            </div>
            <div class="quote-card-foot">
              <span class="quote-date">${script.date} ${escapeHTML(script.timecode)}</span>
              <div class="quote-actions">
                <button type="button" class="quote-btn" data-copy-quote="${script.id}">复制</button>
                <button type="button" class="quote-btn${collected ? " active" : ""}" data-collect-id="${script.id}">${collected ? "已加入合集" : "加入合集"}</button>
              </div>
            </div>
          </article>
        `;
      }).join("") : `<div class="collection-empty">当前场景暂无优质话术</div>`;

      const collectedScripts = QUALITY_SCRIPTS.filter(script => state.scriptCollection.has(script.id));
      $("#qualityCollectionList").innerHTML = collectedScripts.length ? collectedScripts.map((script, index) => {
        const anchor = QUALITY_META[script.accountId];
        return `
          <div class="collection-item">
            <span class="collection-item-index">${String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>${escapeHTML(anchor.name)} · ${escapeHTML(script.scene)}</strong>
              <p>${escapeHTML(script.quote)}</p>
            </div>
            <button type="button" class="collection-remove" data-remove-collection="${script.id}" aria-label="从合集移除">×</button>
          </div>
        `;
      }).join("") : `<div class="collection-empty">从左侧话术卡片点击“加入合集”，这里会生成跨主播参考版本。</div>`;
      const anchorCount = new Set(collectedScripts.map(script => script.accountId)).size;
      $("#qualityCollectionMeta").textContent = `${collectedScripts.length} 条 · ${anchorCount} 位主播 · 10/16 更新`;
      $("#collectionVersion").textContent = state.scriptCollectionVersion;
      $("#qualityTabCount").textContent = QUALITY_SCRIPTS.length;
    }

    function renderLowScripts() {
      const filtered = LOW_SCRIPTS.filter(script =>
        (state.lowAnchor === "all" || script.accountId === state.lowAnchor) &&
        (state.lowScene === "all" || script.scene === state.lowScene)
      );
      const pending = filtered.filter(script => script.status === "待优化").length;
      const averageConversion = filtered.length
        ? filtered.reduce((total, script) => total + script.conversion, 0) / filtered.length
        : 0;
      const averageDwell = filtered.length
        ? filtered.reduce((total, script) => total + script.dwell, 0) / filtered.length
        : 0;
      $("#lowSummary").innerHTML = `
        <div class="low-summary-item"><span>当前清单</span><strong>${filtered.length} 条</strong><em>${pending} 条待优化</em></div>
        <div class="low-summary-item"><span>平均转化率</span><strong>${averageConversion.toFixed(1)}%</strong><em>低于对应主播基线</em></div>
        <div class="low-summary-item"><span>平均停留</span><strong>${averageDwell.toFixed(1)}s</strong><em>语句结束后 30 秒</em></div>
      `;
      $("#lowList").innerHTML = filtered.length ? filtered.map(script => {
        const anchor = QUALITY_META[script.accountId];
        const loss = (script.conversion - script.baseline) / script.baseline * 100;
        const optimized = script.status === "已优化";
        return `
          <article class="low-card${optimized ? " optimized" : ""}">
            <div>
              <div class="low-quote-top">
                <span class="mini-tag ${optimized ? "good" : "warn"}">${optimized ? "已优化" : "持续低效"}</span>
                <span class="mini-tag">${escapeHTML(anchor.name)}</span>
                <span class="mini-tag blue">${escapeHTML(script.scene)}</span>
                <span class="quote-date">近 3 场出现 ${script.occurrences} 次 · ${escapeHTML(script.lastSeen)}</span>
              </div>
              <blockquote>“${escapeHTML(script.quote)}”</blockquote>
              <p class="low-suggestion"><strong>建议：</strong>${escapeHTML(script.suggestion)}</p>
            </div>
            <div class="low-metrics">
              <div class="low-metric"><span>转化率 / 基线</span><strong class="bad">${script.conversion.toFixed(1)}% / ${script.baseline.toFixed(1)}%</strong></div>
              <div class="low-metric"><span>相对基线</span><strong class="bad">${loss.toFixed(0)}%</strong></div>
              <div class="low-metric"><span>平均停留</span><strong>${script.dwell.toFixed(1)}s</strong></div>
              <div class="low-metric"><span>处理状态</span><strong>${optimized ? "待下场验证" : "待调整"}</strong></div>
            </div>
            <div class="low-action">
              <span class="mini-tag ${optimized ? "good" : "warn"}">${optimized ? "V3 已处理" : "本版新增"}</span>
              <button type="button" class="low-mark-btn" data-mark-low="${script.id}">${optimized ? "恢复待优化" : "标记已优化"}</button>
            </div>
          </article>
        `;
      }).join("") : `<div class="collection-empty">当前筛选条件下没有低效话术</div>`;
      $("#lowTabCount").textContent = LOW_SCRIPTS.length;
    }

    function ensureScriptLiveRows() {
      if (state.scriptLiveAccountId === ACTIVE_ACCOUNT.id && state.scriptLiveRows.length) return;
      const source = SCRIPT_LIVE[ACTIVE_ACCOUNT.id] || SCRIPT_LIVE.fashion;
      const baseTime = 20 * 3600 + 46 * 60 + 12;
      state.scriptLiveRows = source.sentences.slice(0, 6).map((item, index) => ({
        ...item,
        id: `${ACTIVE_ACCOUNT.id}-seed-${index}`,
        time: baseTime + index * 47,
        status: "ready",
        comments: [
          source.comments[(index * 2) % source.comments.length],
          source.comments[(index * 2 + 1) % source.comments.length]
        ]
      }));
      state.scriptLiveSourceIndex = Math.min(6, source.sentences.length);
      state.scriptLiveAccountId = ACTIVE_ACCOUNT.id;
    }

    function pushScriptLiveSentence() {
      ensureScriptLiveRows();
      const source = SCRIPT_LIVE[ACTIVE_ACCOUNT.id] || SCRIPT_LIVE.fashion;
      if (!source.sentences.length) return;
      const item = source.sentences[state.scriptLiveSourceIndex % source.sentences.length];
      const index = state.scriptLiveSourceIndex;
      state.scriptLiveSourceIndex += 1;
      const lastTime = state.scriptLiveRows.at(-1)?.time || 20 * 3600;
      const id = `${ACTIVE_ACCOUNT.id}-live-${Date.now()}`;
      const row = {
        ...item,
        id,
        time: lastTime + 43,
        status: "pending",
        readyAt: Date.now() + 4000,
        comments: [
          source.comments[(index * 2) % source.comments.length],
          source.comments[(index * 2 + 1) % source.comments.length]
        ]
      };
      state.scriptLiveRows.push(row);
      if (state.scriptLiveRows.length > 18) state.scriptLiveRows.shift();
      renderScriptLive();
      window.setTimeout(() => {
        const current = state.scriptLiveRows.find(entry => entry.id === id);
        if (!current || current.status === "ready") return;
        current.status = "ready";
        if (state.view === "script" && state.scriptTab === "live") {
          renderScriptLive();
          renderScriptOverview();
        }
      }, 4000);
    }

    function renderScriptLive() {
      ensureScriptLiveRows();
      const live = DIAG_LIVE[ACTIVE_ACCOUNT.id]?.live;
      const rows = state.scriptLiveRows;
      const readyRows = rows.filter(row => row.status === "ready");
      const pendingRows = rows.filter(row => row.status === "pending");
      const latestReady = readyRows.at(-1);

      $("#scriptLiveStatus").textContent = !live
        ? "未开播 · 演示回放"
        : state.scriptLivePaused
          ? "已暂停"
          : pendingRows.length
            ? "4 秒归因中"
            : "实时捕捉中";
      const pauseButton = $("#scriptLivePause");
      pauseButton.textContent = state.scriptLivePaused ? "继续捕捉" : "暂停捕捉";
      pauseButton.disabled = !live;

      if (!$("#scriptLiveWave").children.length) {
        const heights = [10, 18, 26, 14, 32, 22, 38, 18, 28, 12, 24, 34, 16, 30, 20, 36, 14, 26, 18, 22, 30, 16];
        $("#scriptLiveWave").innerHTML = heights.map((height, index) =>
          `<i style="height:${height}px;animation-delay:${(index % 7) * 0.11}s;"></i>`
        ).join("");
      }

      const recentReady = readyRows.slice(-8);
      const averageDwell = recentReady.length
        ? recentReady.reduce((total, row) => total + row.dwellDelta, 0) / recentReady.length
        : 0;
      const totalComments = recentReady.reduce((total, row) => total + row.commentDelta, 0);
      const totalOrders = recentReady.reduce((total, row) => total + row.orderDelta, 0);
      const averageScore = recentReady.length
        ? recentReady.reduce((total, row) => total + row.score, 0) / recentReady.length
        : 0;
      $("#scriptLiveKpis").innerHTML = `
        <div class="script-live-kpi"><span>平均停留影响</span><strong>${formatSigned(averageDwell, 1, "s")}</strong><em>最近 ${recentReady.length} 句</em></div>
        <div class="script-live-kpi"><span>评论增量</span><strong>${formatSigned(totalComments, 0)}</strong><em>归因后的新增评论</em></div>
        <div class="script-live-kpi"><span>成交归因</span><strong>${formatSigned(totalOrders, 0)}</strong><em>订单增量</em></div>
        <div class="script-live-kpi"><span>话术综合分</span><strong>${averageScore ? Math.round(averageScore) : "—"}</strong><em>80 分以上为优质</em></div>
      `;

      $("#scriptLiveFeed").innerHTML = rows.slice(-12).reverse().map(row => {
        const tone = row.tag === "高转化" ? "good" : row.tag === "高停留" ? "blue" : row.tag === "风险" ? "bad" : "warn";
        if (row.status === "pending") {
          const remaining = Math.max(0, Math.ceil((row.readyAt - Date.now()) / 1000));
          return `
            <article class="live-sentence pending">
              <div class="live-sentence-top">
                <span class="live-sentence-time">${formatClock(row.time)}</span>
                <span class="mini-tag warn">分析中</span>
              </div>
              <blockquote>“${escapeHTML(row.text)}”</blockquote>
              <div class="live-sentence-metrics">
                <span class="pending-note"><i></i><span data-pending-note="${row.id}">等待 4 秒归因 · ${remaining}s</span></span>
              </div>
            </article>
          `;
        }
        return `
          <article class="live-sentence">
            <div class="live-sentence-top">
              <span class="live-sentence-time">${formatClock(row.time)}</span>
              <span class="mini-tag ${tone}">${escapeHTML(row.tag)}</span>
            </div>
            <blockquote>“${escapeHTML(row.text)}”</blockquote>
            <div class="live-sentence-metrics">
              <span class="live-delta ${row.commentDelta >= 0 ? "good" : "bad"}">评论 <strong>${formatSigned(row.commentDelta, 0)}</strong></span>
              <span class="live-delta ${row.dwellDelta >= 0 ? "good" : "bad"}">停留 <strong>${formatSigned(row.dwellDelta, 1, "s")}</strong></span>
              <span class="live-delta ${row.orderDelta >= 0 ? "good" : "bad"}">成交 <strong>${formatSigned(row.orderDelta, 0)}</strong></span>
              <span class="live-delta">影响分 <strong>${row.score}</strong></span>
            </div>
          </article>
        `;
      }).join("");

      $("#scriptLiveCurrentQuote").textContent = latestReady ? `“${latestReady.text}”` : "等待实时语句…";
      $("#scriptLiveCurrentMetrics").innerHTML = latestReady ? [
        ["评论", formatSigned(latestReady.commentDelta, 0), latestReady.commentDelta >= 0 ? "good" : "bad"],
        ["停留", formatSigned(latestReady.dwellDelta, 1, "s"), latestReady.dwellDelta >= 0 ? "good" : "bad"],
        ["成交", formatSigned(latestReady.orderDelta, 0), latestReady.orderDelta >= 0 ? "good" : "bad"],
        ["影响分", String(latestReady.score), latestReady.score >= 80 ? "good" : "bad"]
      ].map(([label, value, tone]) => `
        <div class="live-current-metric"><span>${label}</span><strong class="${tone === "bad" ? "bad" : ""}" style="${tone === "good" ? "color:var(--accent-strong);" : tone === "bad" ? "color:var(--danger);" : ""}">${value}</strong></div>
      `).join("") : `<div class="collection-empty" style="grid-column:1/-1;">等待第一句完成归因</div>`;

      const commentSources = readyRows.slice(-3).reverse();
      const commentCount = commentSources.reduce((total, row) => total + row.comments.length, 0);
      $("#scriptLiveCommentMeta").textContent = `近 3 句 · ${commentCount} 条`;
      $("#scriptLiveComments").innerHTML = commentSources.flatMap((row, index) =>
        row.comments.map((comment, commentIndex) => `
          <div class="live-comment">
            <span class="live-comment-avatar">${escapeHTML(comment.slice(0, 1))}</span>
            <div>
              <p>${escapeHTML(comment)}</p>
              <time>${formatClock(row.time + 5 + infoDelay(index, commentIndex))}</time>
            </div>
          </div>
        `)
      ).join("");

      $("#scriptImpactMeta").textContent = `${readyRows.length} 句已归因 · 延迟 4 秒`;
      if (state.scriptTab === "live") renderScriptImpactChart();
    }

    function infoDelay(index, commentIndex) {
      return index * 3 + commentIndex * 2;
    }

    function renderScriptImpactChart() {
      const svg = $("#scriptImpactChart");
      const wrap = $("#scriptImpactChartWrap");
      if (!svg || !wrap) return;
      const rows = state.scriptLiveRows.filter(row => row.status === "ready").slice(-10);
      svg.replaceChildren();
      if (!rows.length || !wrap.clientWidth) return;
      const width = Math.max(320, wrap.clientWidth);
      const height = Math.max(180, wrap.clientHeight || 220);
      const margin = { top: 18, right: 18, bottom: 30, left: 36 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const bottom = margin.top + innerHeight;
      const xFor = index => margin.left + (rows.length === 1 ? innerWidth / 2 : index / (rows.length - 1) * innerWidth);
      const maxComments = Math.max(32, ...rows.map(row => row.commentDelta));
      const minDwell = Math.min(-4, ...rows.map(row => row.dwellDelta));
      const maxDwell = Math.max(10, ...rows.map(row => row.dwellDelta));
      const yDwell = value => margin.top + (maxDwell - value) / (maxDwell - minDwell) * innerHeight;
      const maxOrders = Math.max(14, ...rows.map(row => row.orderDelta));
      const barMax = innerHeight * 0.38;
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

      for (let index = 0; index <= 4; index += 1) {
        const y = margin.top + innerHeight / 4 * index;
        svg.appendChild(svgElement("line", {
          x1: margin.left, y1: y, x2: width - margin.right, y2: y,
          stroke: "#e8ece7", "stroke-width": "1", "stroke-dasharray": index === 4 ? "0" : "2 4"
        }));
      }
      const zeroY = yDwell(0);
      svg.appendChild(svgElement("line", {
        x1: margin.left, y1: zeroY, x2: width - margin.right, y2: zeroY,
        stroke: "#c9d4cb", "stroke-width": "1"
      }));

      const barWidth = Math.max(6, Math.min(24, innerWidth / Math.max(1, rows.length) * 0.34));
      rows.forEach((row, index) => {
        const x = xFor(index);
        const commentHeight = Math.abs(row.commentDelta) / maxComments * barMax;
        svg.appendChild(svgElement("rect", {
          x: x - barWidth / 2,
          y: bottom - commentHeight,
          width: barWidth,
          height: commentHeight,
          rx: 3,
          fill: row.commentDelta >= 0 ? "rgba(11,122,88,0.26)" : "rgba(182,77,61,0.26)"
        }));
        svg.appendChild(svgElement("circle", {
          cx: x,
          cy: bottom - (Math.max(0, row.orderDelta) / maxOrders) * innerHeight * 0.34 - 4,
          r: 3.2,
          fill: "#c9723c",
          stroke: "#fff",
          "stroke-width": "1.5"
        }));
        const hit = svgElement("rect", {
          x: x - Math.max(14, innerWidth / rows.length / 2),
          y: margin.top,
          width: Math.max(28, innerWidth / rows.length),
          height: innerHeight,
          fill: "transparent"
        });
        const title = document.createElementNS(svgNS, "title");
        title.textContent = `${formatClock(row.time)} ${row.text}\n评论 ${formatSigned(row.commentDelta, 0)} · 停留 ${formatSigned(row.dwellDelta, 1, "s")} · 成交 ${formatSigned(row.orderDelta, 0)}`;
        hit.appendChild(title);
        svg.appendChild(hit);
      });

      const linePath = rows.map((row, index) =>
        `${index === 0 ? "M" : "L"} ${xFor(index).toFixed(1)} ${yDwell(row.dwellDelta).toFixed(1)}`
      ).join(" ");
      svg.appendChild(svgElement("path", {
        d: linePath,
        fill: "none",
        stroke: "#2b6f94",
        "stroke-width": "2.2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      }));
      rows.forEach((row, index) => {
        svg.appendChild(svgElement("circle", {
          cx: xFor(index), cy: yDwell(row.dwellDelta), r: 3.3,
          fill: "#fff", stroke: "#2b6f94", "stroke-width": "2"
        }));
      });

      [maxDwell, 0, minDwell].forEach(value => {
        if (value < minDwell || value > maxDwell) return;
        const label = svgElement("text", {
          x: margin.left - 7,
          y: yDwell(value) + 3,
          "text-anchor": "end",
          fill: "#8a978f",
          "font-size": "8",
          "font-variant-numeric": "tabular-nums"
        });
        label.textContent = formatSigned(value, 0, "s");
        svg.appendChild(label);
      });
      const dwellLabel = svgElement("text", {
        x: margin.left, y: 10, fill: "#2b6f94", "font-size": "8", "font-weight": "700"
      });
      dwellLabel.textContent = "停留变化";
      svg.appendChild(dwellLabel);
      const commentLabel = svgElement("text", {
        x: width - margin.right, y: 10, "text-anchor": "end", fill: "#718078", "font-size": "8", "font-weight": "700"
      });
      commentLabel.textContent = "评论增量 / 成交节点";
      svg.appendChild(commentLabel);

      const labelIndexes = new Set([0, rows.length - 1]);
      if (rows.length > 4) labelIndexes.add(Math.round((rows.length - 1) / 2));
      labelIndexes.forEach(index => {
        const label = svgElement("text", {
          x: xFor(index),
          y: height - 9,
          "text-anchor": index === 0 ? "start" : index === rows.length - 1 ? "end" : "middle",
          fill: "#8a978f",
          "font-size": "8",
          "font-variant-numeric": "tabular-nums"
        });
        label.textContent = formatClock(rows[index].time).slice(0, 5);
        svg.appendChild(label);
      });
    }

    function renderCampaignPage() {
      const data = CAMPAIGN_DATA[ACTIVE_ACCOUNT.id] || CAMPAIGN_DATA.fashion;
      const live = DIAG_LIVE[ACTIVE_ACCOUNT.id]?.live;
      const chip = $("#campaignLiveChip");
      if (chip) {
        chip.className = `live-chip${live ? "" : " offline"}`;
        chip.innerHTML = `<i></i>${live ? "实时采集中" : "未开播 · 演示数据"}`;
      }
      if (!state.campaignSyncedAt) state.campaignSyncedAt = new Date();
      const syncTime = state.campaignSyncedAt.toLocaleTimeString("zh-CN", { hour12: false });
      $("#campaignSyncText").innerHTML = `<i></i>${live ? "数据截止" : "演示数据截止"} ${syncTime} · 30 秒刷新`;
      const trafficBadge = $("#campaignTrafficBadge");
      trafficBadge.textContent = live ? "实时采集" : "演示数据";
      trafficBadge.className = `mini-tag ${live ? "good" : "warn"}`;

      renderCampaignLiveStrip(data);
      renderCampaignTraffic(data);
      renderCampaignDecision(data);
      renderCampaignDocs(data);
      renderCampaignOperations(data);
      renderCampaignEffectAndLog(data);
      renderCampaignAnomaly(data);
    }

    function renderCampaignLiveStrip(data) {
      const summary = data.summary;
      const tick = state.campaignTick;
      const liveSpendRate = Math.round(summary.spendRate * (1 + Math.sin(tick / 3.1) * 0.012));
      const liveOrders = Math.round(summary.orders + Math.sin(tick / 4.2) * 3);
      const liveRoi = summary.roi + Math.sin(tick / 5.5) * 0.03;
      const liveOnline = Math.round(summary.online * (1 + Math.sin(tick / 2.4) * 0.006));
      $("#campaignLiveStrip").innerHTML = [
        ["今日消耗", `¥${formatNumber(summary.spend / 10000, 2)}万`, "+8.4% 较上小时", "good"],
        ["消耗 / 时", `¥${formatNumber(liveSpendRate, 0)}`, "实时采集", ""],
        ["成交订单", formatNumber(liveOrders, 0), "+6.2% 较上小时", "good"],
        ["ROI", liveRoi.toFixed(2), `目标 4.00 · ${liveRoi >= 4 ? "已达成" : "待提升"}`, liveRoi >= 4 ? "good" : "bad"],
        ["付费流量", `${summary.paidShare}%`, `自然推荐 ${data.channels.find(channel => channel.name === "自然推荐")?.share || 0}%`, ""],
        ["在线人数", formatNumber(liveOnline, 0), "+4.1% 较 5 分钟前", "good"]
      ].map(([label, value, note, tone]) => `
        <div class="campaign-live-cell">
          <span>${label}</span>
          <strong>${value}</strong>
          <em class="${tone}">${note}</em>
        </div>
      `).join("");
    }

    function renderCampaignTraffic(data) {
      const donut = $("#campaignDonut");
      let angle = 0;
      const stops = data.channels.map(channel => {
        const start = angle;
        angle += channel.share;
        return `${channel.color} ${start}% ${angle}%`;
      });
      donut.style.background = `conic-gradient(${stops.join(", ")})`;
      $("#campaignPaidShare").textContent = `${data.summary.paidShare}%`;

      $("#campaignChannelList").innerHTML = data.channels.map(channel => `
        <div class="channel-row">
          <span class="channel-name"><i class="channel-dot" style="background:${channel.color};"></i>${escapeHTML(channel.name)}</span>
          <strong>${channel.share}%</strong>
        </div>
      `).join("");

      $("#campaignChannelTable").innerHTML = `
        <div class="channel-table-row" style="color:var(--muted);font-weight:700;">
          <span>渠道</span><span style="text-align:right;">占比</span><span style="text-align:right;">消耗 / 时</span><span style="text-align:right;">ROI</span>
        </div>
        ${data.channels.map(channel => `
          <div class="channel-table-row">
            <span class="channel-name"><i class="channel-dot" style="background:${channel.color};"></i>${escapeHTML(channel.name)}
              <em class="${channel.trend >= 0 ? "trend-up" : "trend-down"}" style="font-style:normal;font-size:7.5px;">${formatSigned(channel.trend, 1, "%")}</em>
            </span>
            <strong>${channel.share}%</strong>
            <strong>${channel.spend ? `¥${formatNumber(channel.spend, 0)}` : "自然"}</strong>
            <strong>${channel.roi.toFixed(1)}</strong>
          </div>
        `).join("")}
      `;

      const persona = data.persona;
      const barGroup = (title, note, values) => `
        <div class="persona-title" style="margin-top:10px;">${title}<span>${note}</span></div>
        <div class="persona-bars">
          ${values.map(([label, value]) => `
            <div class="persona-bar">
              <span>${escapeHTML(label)}</span>
              <div class="persona-track"><i style="width:${value}%;"></i></div>
              <strong>${value}%</strong>
            </div>
          `).join("")}
        </div>
      `;
      $("#campaignPersona").innerHTML = `
        ${barGroup("性别", "实时识别", persona.gender)}
        ${barGroup("年龄", "成交人群", persona.age)}
        <div class="persona-title" style="margin-top:10px;">地域<span>成交占比</span></div>
        <div style="color:var(--muted);font-size:8.5px;line-height:1.5;">${escapeHTML(persona.region)}</div>
        <div class="persona-tags">${persona.tags.map(tag => `<span class="mini-tag">${escapeHTML(tag)}</span>`).join("")}</div>
      `;
    }

    function renderCampaignDecision(data) {
      const daypart = data.decisions[state.campaignDaypart] || data.decisions.evening;
      $$("#campaignDayparts button").forEach(button => {
        button.classList.toggle("active", button.dataset.campaignDaypart === state.campaignDaypart);
      });
      $("#campaignSignals").innerHTML = data.signals.map(signal => `
        <div class="signal-card">
          <span>${escapeHTML(signal.label)}</span>
          <strong>${escapeHTML(signal.value)}</strong>
          <em>${escapeHTML(signal.note)}</em>
        </div>
      `).join("");
      $("#campaignDecision").innerHTML = `
        <div class="decision-label">建议动作 <span>置信度 ${daypart.confidence}%</span></div>
        <div class="decision-action">${escapeHTML(daypart.action)}<em>${daypart.percent > 0 ? `+${daypart.percent}%` : "暂停"}</em></div>
        <p class="decision-reason">${escapeHTML(daypart.reason)}</p>
        <div class="decision-chips">${daypart.expected.map(item => `<span>${escapeHTML(item)}</span>`).join("")}</div>
        <div class="decision-guardrail">止损边界：${escapeHTML(daypart.guardrail)}</div>
      `;
    }

    function renderCampaignDocs(data) {
      $("#campaignDocs").innerHTML = data.docs.length ? data.docs.map(doc => `
        <div class="doc-item">
          <span class="doc-icon">${escapeHTML(doc.type)}</span>
          <div class="doc-copy">
            <strong title="${escapeHTML(doc.name)}">${escapeHTML(doc.name)}</strong>
            <span>${escapeHTML(doc.size)} · ${escapeHTML(doc.date)} · ${doc.rules ? `提取 ${doc.rules} 条规则` : "等待解析"}</span>
          </div>
          <span class="mini-tag doc-status ${doc.status === "已学习" ? "good" : "warn"}">${doc.status === "已学习" ? "已学习" : "解析中"}</span>
        </div>
      `).join("") : `<div class="collection-empty">还没有上传文档</div>`;
      $("#campaignRuleCount").textContent = `${data.rules.length} 条规则`;
      $("#campaignRules").innerHTML = data.rules.map((rule, index) => `
        <div class="rule-row"><strong>${String(index + 1).padStart(2, "0")}</strong><span>${escapeHTML(rule)}</span></div>
      `).join("");
    }

    function renderCampaignOperations(data) {
      if (!state.campaignOperations.length) {
        state.campaignOperations.push({
          accountId: ACTIVE_ACCOUNT.id,
          time: "20:32",
          action: "控成本追投",
          percent: 6,
          note: "30 分钟 ROI 4.21 → 4.34，订单 +7.2%",
          demo: true
        });
      }
      $("#campaignOperations").innerHTML = CAMPAIGN_ACTIONS.map((action, index) => `
        <article class="operation-card" data-operation-id="${action.id}">
          <div class="op-head">
            <div>
              <span class="op-index">${String(index + 1).padStart(2, "0")}</span>
              <strong>${action.title}</strong>
            </div>
            <span class="mini-tag warn">示例</span>
          </div>
          <p>${action.desc}</p>
          <div class="op-control">
            <span>调整幅度</span>
            <strong data-op-value>${action.direction < 0 ? "-" : "+"}${action.value}%</strong>
          </div>
          <input type="range" class="op-range" data-op-range min="${action.min}" max="${action.max}" value="${action.value}" step="1" aria-label="${action.title}调整幅度">
          <button type="button" class="op-run-btn" data-run-op="${action.id}">演示执行</button>
        </article>
      `).join("");
    }

    function renderCampaignEffectAndLog(data) {
      const effect = state.campaignLastEffect;
      if (!effect || effect.accountId !== ACTIVE_ACCOUNT.id) {
        $("#campaignEffect").innerHTML = `
          <div class="subsection-head"><h3>操作后影响</h3><span>示例归因</span></div>
          <div class="collection-empty" style="margin-top:8px;">执行任一操作后，这里会展示 30 分钟消耗、ROI、在线人数与订单变化。</div>
        `;
      } else {
        const effectPercent = effect.percent > 0 ? `+${effect.percent}%` : `${effect.percent}%`;
        const rows = [
          ["消耗 / 时", effect.before.spendRate, effect.after.spendRate, value => `¥${formatNumber(value, 0)}`],
          ["ROI", effect.before.roi, effect.after.roi, value => value.toFixed(2)],
          ["在线人数", effect.before.online, effect.after.online, value => formatNumber(value, 0)],
          ["订单 / 时", effect.before.ordersRate, effect.after.ordersRate, value => formatNumber(value, 0)]
        ];
        $("#campaignEffect").innerHTML = `
          <div class="subsection-head"><h3>操作后影响</h3><span>${escapeHTML(effect.time)} · ${escapeHTML(effect.action)} ${effect.percent ? effectPercent : ""}</span></div>
          <div class="effect-grid">
            ${rows.map(([label, before, after, format]) => {
              const delta = before ? (after - before) / before * 100 : 0;
              return `
                <div class="effect-row">
                  <span>${label}</span>
                  <div class="effect-arrow"><strong>${format(before)}</strong><i></i><strong>${format(after)}</strong></div>
                  <strong class="${delta >= 0 ? "trend-up" : "trend-down"}">${formatSigned(delta, 1, "%")}</strong>
                </div>
              `;
            }).join("")}
          </div>
          <div class="note-copy">示例归因，不代表千川后台真实结果；接入 API 后按操作时间回读。</div>
        `;
      }

      $("#campaignOpCount").textContent = `${state.campaignOperations.length} 次`;
      $("#campaignOperationLog").innerHTML = state.campaignOperations.slice(0, 5).map(operation => `
        <div class="operation-log-row">
          <div>
            <strong>${escapeHTML(operation.action)}${operation.percent ? ` ${operation.percent > 0 ? "+" : ""}${operation.percent}%` : ""}</strong>
            <span> · ${escapeHTML(operation.note)}</span>
          </div>
          <em>${escapeHTML(operation.time)}</em>
        </div>
      `).join("");
    }

    function renderCampaignAnomaly(data) {
      const anomalies = data.anomalies || [];
      $("#campaignAnomalySummary").textContent = anomalies.length ? `识别到 ${anomalies.length} 个异常时段` : "暂无异常";
      $("#campaignAnomalyList").innerHTML = anomalies.length ? anomalies.map(item => `
        <div class="anomaly-item">
          <span class="anomaly-time">${escapeHTML(item.time)}</span>
          <div class="anomaly-copy">
            <strong>${escapeHTML(item.metric)}</strong>
            <p>${escapeHTML(item.cause)}</p>
            <em>建议：${escapeHTML(item.suggestion)}</em>
          </div>
          <span class="mini-tag ${item.severity === "高" ? "bad" : "warn"}">${escapeHTML(item.severity)}风险</span>
        </div>
      `).join("") : `<div class="collection-empty">当前时段没有识别到流量异常</div>`;
      window.requestAnimationFrame(() => renderCampaignAnomalyChart(data));
    }

    function renderCampaignAnomalyChart(data) {
      const svg = $("#campaignAnomalyChart");
      const wrap = svg?.parentElement;
      if (!svg || !wrap || !wrap.clientWidth) return;
      const points = data.series;
      if (!points.length) return;
      const width = Math.max(320, wrap.clientWidth);
      const height = Math.max(180, wrap.clientHeight || 220);
      const margin = { top: 18, right: 18, bottom: 28, left: 34 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const bottom = margin.top + innerHeight;
      const xFor = index => margin.left + (points.length === 1 ? innerWidth / 2 : index / (points.length - 1) * innerWidth);
      const maxSpend = Math.max(40, ...points.map(point => point.spend));
      const roiMin = Math.min(2.4, ...points.map(point => point.roi));
      const roiMax = Math.max(5, ...points.map(point => point.roi));
      const yRoi = value => margin.top + (roiMax - value) / (roiMax - roiMin) * innerHeight;
      svg.replaceChildren();
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

      for (let index = 0; index <= 4; index += 1) {
        const y = margin.top + innerHeight / 4 * index;
        svg.appendChild(svgElement("line", {
          x1: margin.left, y1: y, x2: width - margin.right, y2: y,
          stroke: "#e8ece7", "stroke-width": "1", "stroke-dasharray": index === 4 ? "0" : "2 4"
        }));
      }

      points.forEach((point, index) => {
        if (point.flagged) {
          svg.appendChild(svgElement("rect", {
            x: xFor(index) - innerWidth / points.length / 2,
            y: margin.top,
            width: Math.max(18, innerWidth / points.length),
            height: innerHeight,
            fill: "rgba(201,114,60,0.08)"
          }));
        }
        const barHeight = point.spend / maxSpend * innerHeight * 0.42;
        svg.appendChild(svgElement("rect", {
          x: xFor(index) - 5,
          y: bottom - barHeight,
          width: 10,
          height: barHeight,
          rx: 3,
          fill: point.flagged ? "rgba(201,114,60,0.35)" : "rgba(11,122,88,0.16)"
        }));
      });

      const linePath = points.map((point, index) =>
        `${index === 0 ? "M" : "L"} ${xFor(index).toFixed(1)} ${yRoi(point.roi).toFixed(1)}`
      ).join(" ");
      svg.appendChild(svgElement("path", {
        d: linePath,
        fill: "none",
        stroke: "#2b6f94",
        "stroke-width": "2.2",
        "stroke-linecap": "round",
        "stroke-linejoin": "round"
      }));
      points.forEach((point, index) => {
        svg.appendChild(svgElement("circle", {
          cx: xFor(index),
          cy: yRoi(point.roi),
          r: point.flagged ? 4.4 : 3,
          fill: point.flagged ? "#c9723c" : "#fff",
          stroke: point.flagged ? "#c9723c" : "#2b6f94",
          "stroke-width": "2"
        }));
        const hit = svgElement("rect", {
          x: xFor(index) - Math.max(12, innerWidth / points.length / 2),
          y: margin.top,
          width: Math.max(24, innerWidth / points.length),
          height: innerHeight,
          fill: "transparent"
        });
        const title = document.createElementNS(svgNS, "title");
        title.textContent = `${point.label} 消耗指数 ${point.spend} · ROI ${point.roi.toFixed(1)} · 在线 ${point.online}万${point.flagged ? " · 异常" : ""}`;
        hit.appendChild(title);
        svg.appendChild(hit);
      });

      [roiMax, (roiMax + roiMin) / 2, roiMin].forEach(value => {
        const label = svgElement("text", {
          x: margin.left - 7,
          y: yRoi(value) + 3,
          "text-anchor": "end",
          fill: "#8a978f",
          "font-size": "8",
          "font-variant-numeric": "tabular-nums"
        });
        label.textContent = value.toFixed(1);
        svg.appendChild(label);
      });
      const labelIndexes = new Set([0, points.length - 1]);
      if (points.length > 5) labelIndexes.add(Math.round((points.length - 1) / 2));
      labelIndexes.forEach(index => {
        const label = svgElement("text", {
          x: xFor(index),
          y: height - 8,
          "text-anchor": index === 0 ? "start" : index === points.length - 1 ? "end" : "middle",
          fill: "#8a978f",
          "font-size": "8",
          "font-variant-numeric": "tabular-nums"
        });
        label.textContent = points[index].label;
        svg.appendChild(label);
      });
      const roiLabel = svgElement("text", {
        x: margin.left, y: 10, fill: "#2b6f94", "font-size": "8", "font-weight": "700"
      });
      roiLabel.textContent = "ROI 走势";
      svg.appendChild(roiLabel);
      const spendLabel = svgElement("text", {
        x: width - margin.right, y: 10, "text-anchor": "end", fill: "#718078", "font-size": "8", "font-weight": "700"
      });
      spendLabel.textContent = "柱形：消耗指数";
      svg.appendChild(spendLabel);
    }

    function handleCampaignDocFiles(files) {
      const accountId = ACTIVE_ACCOUNT.id;
      const data = CAMPAIGN_DATA[accountId];
      if (!data) return;
      const incoming = Array.from(files || []);
      if (!incoming.length) return;
      const created = incoming.map((file, index) => {
        const extension = (file.name.split(".").pop() || "FILE").toUpperCase();
        const doc = {
          id: `doc-upload-${Date.now()}-${index}`,
          name: file.name,
          type: extension,
          size: file.size > 1024 * 1024 ? `${(file.size / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(file.size / 1024))} KB`,
          status: "解析中",
          rules: 0,
          date: "今天"
        };
        data.docs.unshift(doc);
        return doc;
      });
      renderCampaignDocs(data);
      showToast(`已上传 ${created.length} 份文档，正在解析投放节奏`);
      created.forEach((doc, index) => {
        window.setTimeout(() => {
          const target = CAMPAIGN_DATA[accountId]?.docs.find(item => item.id === doc.id);
          if (!target) return;
          target.status = "已学习";
          target.rules = 1 + (index % 2);
          const rule = CAMPAIGN_RULE_POOL[(state.campaignDocSeq + index) % CAMPAIGN_RULE_POOL.length];
          CAMPAIGN_DATA[accountId].rules.push(rule);
          state.campaignDocSeq += 1;
          if (ACTIVE_ACCOUNT.id === accountId) renderCampaignDocs(CAMPAIGN_DATA[accountId]);
          if (state.view === "campaign" && ACTIVE_ACCOUNT.id === accountId) {
            showToast(`《${fileShortName(doc.name)}》已学习，新增 ${target.rules} 条节奏规则`);
          }
        }, 1200 + index * 320);
      });
    }

    function fileShortName(name) {
      const value = String(name || "");
      return value.length > 18 ? `${value.slice(0, 16)}…` : value;
    }

    function runCampaignAction(actionId) {
      const action = CAMPAIGN_ACTIONS.find(item => item.id === actionId);
      const card = document.querySelector(`[data-operation-id="${actionId}"]`);
      const range = card?.querySelector("[data-op-range]");
      if (!action || !range) return;
      const percent = Number(range.value);
      const data = CAMPAIGN_DATA[ACTIVE_ACCOUNT.id];
      if (!data) return;
      const summary = data.summary;
      let spendChange = percent;
      let roiDelta = -percent * 0.006;
      let onlineChange = percent * 0.4;
      let ordersChange = percent * 0.65;
      if (action.kind === "cost") {
        spendChange = percent * 0.9;
        roiDelta = 0.03 + percent * 0.001;
        onlineChange = percent * 0.35;
        ordersChange = percent * 0.6;
      } else if (action.kind === "all") {
        spendChange = percent * 1.05;
        roiDelta = -percent * 0.007;
        onlineChange = percent * 0.45;
        ordersChange = percent * 0.7;
      } else if (action.kind === "reduce") {
        spendChange = -percent * 0.9;
        roiDelta = percent * 0.008;
        onlineChange = -percent * 0.35;
        ordersChange = -percent * 0.25;
      }
      const before = {
        spendRate: summary.spendRate,
        roi: summary.roi,
        online: summary.online,
        ordersRate: summary.ordersRate
      };
      const after = {
        spendRate: before.spendRate * (1 + spendChange / 100),
        roi: Math.max(0, before.roi + roiDelta),
        online: Math.max(0, before.online * (1 + onlineChange / 100)),
        ordersRate: Math.max(0, before.ordersRate * (1 + ordersChange / 100))
      };
      const time = new Date().toLocaleTimeString("zh-CN", { hour12: false }).slice(0, 5);
      const signedPercent = action.direction < 0 ? -percent : percent;
      state.campaignLastEffect = {
        accountId: ACTIVE_ACCOUNT.id,
        action: action.title,
        percent: signedPercent,
        time,
        before,
        after
      };
      state.campaignOperations.unshift({
        accountId: ACTIVE_ACCOUNT.id,
        time,
        action: action.title,
        percent: signedPercent,
        note: `消耗 ${formatSigned(spendChange, 1, "%")} · ROI ${formatSigned(roiDelta, 2)} · 订单 ${formatSigned(ordersChange, 1, "%")}`,
        demo: true
      });
      state.campaignOperations = state.campaignOperations.slice(0, 8);
      renderCampaignEffectAndLog(data);
      showToast(`已生成“${action.title} ${signedPercent > 0 ? "+" : ""}${signedPercent}%”示例结果，未写入千川后台`);
    }

    function renderAll() {
      refreshActiveData();
      const rows = getRange(state.start, state.end);
      const previousRows = getPreviousRange(state.start, state.end);
      updateDateInputs();
      renderPageHeader(rows);
      renderKpis(rows, previousRows);
      renderChart(rows, previousRows);
      renderLiveDiagnosis();
      renderAccountPanel(rows, previousRows);
      renderAccountChrome();
      renderMaterialPage();
      renderReviewPage();
      renderScriptPage();
      renderCampaignPage();
      updateSyncText();
    }

    function setPreset(days) {
      const endIndex = ACTIVE_DATA.length - 1;
      const startIndex = Math.max(0, endIndex - days + 1);
      state.start = ACTIVE_DATA[startIndex].date;
      state.end = ACTIVE_DATA[endIndex].date;
      renderAll();
    }

    const VIEW_LABELS = {
      data: "数据",
      material: "素材",
      diagnosis: "诊断",
      script: "话术",
      campaign: "投放诊断",
      review: "复盘"
    };
    let lastSyncAt = new Date();

    function updateSyncText() {
      $("#syncText").textContent = `千川快照 · 截止 ${ACTIVE_ACCOUNT.dataCutoff}`;
      $("#syncText").title = "数据来自千川全域推广接口，当前页面展示本地快照";
    }

    function setAccountMenu(open) {
      $("#accountMenu").hidden = !open;
      $("#accountTrigger").setAttribute("aria-expanded", String(open));
    }

    function showView(name, updateHash = true) {
      if (!VIEW_LABELS[name]) name = "data";
      state.view = name;
      if (name !== "review") state.playerPlaying = false;
      $$(".nav-item").forEach(button => {
        const active = button.dataset.viewTarget === name;
        button.classList.toggle("active", active);
        if (active) button.setAttribute("aria-current", "page");
        else button.removeAttribute("aria-current");
      });
      const activeNav = $(".nav-item.active");
      if (activeNav) activeNav.scrollIntoView({ inline: "center", block: "nearest" });
      $$("[data-view-panel]").forEach(panel => {
        panel.hidden = panel.dataset.viewPanel !== name;
      });
      $("#datePresets").hidden = name !== "data";
      document.title = `${VIEW_LABELS[name]} · 千川 AI 投放诊断`;
      if (updateHash) {
        try {
          window.history.replaceState(null, "", `#${name}`);
        } catch (error) {
          // 本地文件环境不允许修改 history 时，忽略即可。
        }
      }
      if (name === "data") {
        window.requestAnimationFrame(() => {
          const rows = getRange(state.start, state.end);
          const previousRows = getPreviousRange(state.start, state.end);
          renderChart(rows, previousRows);
          renderAccountPanel(rows, previousRows);
          updateSyncText();
        });
      }
      if (name === "material") renderMaterialPage();
      if (name === "diagnosis") renderLiveDiagnosis();
      if (name === "review") renderReviewPage();
      if (name === "script") {
        renderScriptPage();
        window.requestAnimationFrame(() => {
          $("#scriptTabs button.active")?.scrollIntoView({ inline: "center", block: "nearest" });
        });
        if (state.scriptTab === "live") {
          window.requestAnimationFrame(() => window.setTimeout(renderScriptImpactChart, 20));
        }
      }
      if (name === "campaign") {
        renderCampaignPage();
        window.requestAnimationFrame(() => renderCampaignAnomalyChart(CAMPAIGN_DATA[ACTIVE_ACCOUNT.id] || CAMPAIGN_DATA.fashion));
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    $$("#datePresets button").forEach(button => {
      button.addEventListener("click", () => setPreset(Number(button.dataset.days)));
    });

    $("#materialSearch").addEventListener("input", renderMaterialPage);
    $("#materialType").addEventListener("change", renderMaterialPage);
    $("#materialRefresh").addEventListener("click", () => {
      lastSyncAt = new Date();
      renderMaterialPage();
    });

    function selectScriptTab(tab) {
      if (!["banned", "quality", "low", "live"].includes(tab)) return;
      state.scriptTab = tab;
      renderScriptPage();
      window.requestAnimationFrame(() => {
        $("#scriptTabs button.active")?.scrollIntoView({ inline: "center", block: "nearest" });
      });
      if (tab === "live") {
        window.requestAnimationFrame(() => window.setTimeout(renderScriptImpactChart, 20));
      }
    }

    $$("#scriptTabs button").forEach(button => {
      button.addEventListener("click", () => selectScriptTab(button.dataset.scriptTab));
    });

    $("#scriptJumpLive").addEventListener("click", () => {
      selectScriptTab("live");
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    $("#scriptWordSearch").addEventListener("input", event => {
      state.scriptWordQuery = event.target.value;
      renderBannedLibrary();
    });

    $("#scriptWordCategory").addEventListener("change", event => {
      state.scriptWordCategory = event.target.value;
      renderBannedLibrary();
    });

    $("#scriptWordUploadBtn").addEventListener("click", () => $("#scriptWordInput").click());
    $("#scriptUploadChannels").addEventListener("click", event => {
      if (event.target.closest("[data-upload-word-local]")) $("#scriptWordInput").click();
    });
    $("#scriptWordInput").addEventListener("change", event => {
      handleScriptWordFile(event.target.files[0]);
      event.target.value = "";
    });

    $("#scriptWordPasteToggle").addEventListener("click", () => {
      const box = $("#scriptPasteBox");
      box.hidden = !box.hidden;
      if (!box.hidden) $("#scriptPasteText").focus();
    });
    $("#scriptPasteCancel").addEventListener("click", () => {
      $("#scriptPasteBox").hidden = true;
      $("#scriptPasteText").value = "";
    });
    $("#scriptPasteSubmit").addEventListener("click", () => {
      const words = $("#scriptPasteText").value.split(/\r?\n/).map(word => word.trim()).filter(Boolean);
      if (!words.length) {
        showToast("请先粘贴至少一个词条");
        return;
      }
      const categoryId = $("#scriptPasteCategory").value;
      const entries = words.map((word, index) => ({
        id: `paste-${Date.now()}-${index}`,
        word,
        categoryId,
        level: "mid",
        note: "批量粘贴，待人工复核适用范围。",
        replacement: "待补充替换建议",
        source: "批量粘贴",
        updated: "今天",
        status: "待复核",
        hits: 0
      }));
      addBannedWords(entries, "批量粘贴");
      $("#scriptPasteText").value = "";
      $("#scriptPasteBox").hidden = true;
    });

    $("#qualityAnchorTabs").addEventListener("click", event => {
      const button = event.target.closest("[data-quality-anchor]");
      if (!button) return;
      state.scriptQualityAnchor = button.dataset.qualityAnchor;
      renderQualityScripts();
    });

    $("#qualityScene").addEventListener("change", event => {
      state.scriptQualityScene = event.target.value;
      renderQualityScripts();
    });

    $("#qualityReExtract").addEventListener("click", () => {
      const button = $("#qualityReExtract");
      button.disabled = true;
      button.textContent = "摘取中…";
      window.setTimeout(() => {
        button.disabled = false;
        button.textContent = "重新摘取本场";
        const meta = QUALITY_META[state.scriptQualityAnchor];
        showToast(`已重新分析${meta.session}，命中 ${meta.extracted} 条优质话术`);
      }, 1200);
    });

    $("#qualityScriptGrid").addEventListener("click", event => {
      const copyButton = event.target.closest("[data-copy-quote]");
      if (copyButton) {
        const script = QUALITY_SCRIPTS.find(item => item.id === copyButton.dataset.copyQuote);
        if (script) copyText(`${script.quote}\n场景：${script.scene} · 转化率 ${script.conversion.toFixed(1)}% · 停留 ${script.dwell.toFixed(1)}s`, "话术已复制");
        return;
      }
      const collectButton = event.target.closest("[data-collect-id]");
      if (collectButton) {
        const id = collectButton.dataset.collectId;
        if (state.scriptCollection.has(id)) state.scriptCollection.delete(id);
        else state.scriptCollection.add(id);
        state.scriptCollectionVersion = "V1.8 · 调整中";
        renderQualityScripts();
        renderScriptOverview();
      }
    });

    $("#qualityCollectionList").addEventListener("click", event => {
      const button = event.target.closest("[data-remove-collection]");
      if (!button) return;
      state.scriptCollection.delete(button.dataset.removeCollection);
      state.scriptCollectionVersion = "V1.8 · 调整中";
      renderQualityScripts();
      renderScriptOverview();
    });

    $("#qualityCopyCollection").addEventListener("click", () => {
      const scripts = QUALITY_SCRIPTS.filter(script => state.scriptCollection.has(script.id));
      if (!scripts.length) {
        showToast("合集为空，先加入几条话术");
        return;
      }
      const content = scripts.map((script, index) => {
        const anchor = QUALITY_META[script.accountId];
        return `${index + 1}. ${anchor.name}｜${script.scene}\n${script.quote}\n转化 ${script.conversion.toFixed(1)}% · 停留 ${script.dwell.toFixed(1)}s`;
      }).join("\n\n");
      copyText(`话术参考合集 ${state.scriptCollectionVersion}\n\n${content}`, "话术合集已复制");
    });

    $("#qualitySaveCollection").addEventListener("click", () => {
      if (!state.scriptCollection.size) {
        showToast("合集为空，先加入几条话术");
        return;
      }
      const match = state.scriptCollectionVersion.match(/V1\.(\d+)/);
      const nextVersion = match ? `V1.${Number(match[1]) + 1}` : "V1.9";
      state.scriptCollectionVersion = nextVersion;
      renderQualityScripts();
      renderScriptOverview();
      showToast(`已保存合集 ${nextVersion}，共 ${state.scriptCollection.size} 条`);
    });

    $("#lowAnchor").addEventListener("change", event => {
      state.lowAnchor = event.target.value;
      renderLowScripts();
    });
    $("#lowScene").addEventListener("change", event => {
      state.lowScene = event.target.value;
      renderLowScripts();
    });
    $("#lowList").addEventListener("click", event => {
      const button = event.target.closest("[data-mark-low]");
      if (!button) return;
      const script = LOW_SCRIPTS.find(item => item.id === button.dataset.markLow);
      if (!script) return;
      script.status = script.status === "待优化" ? "已优化" : "待优化";
      renderLowScripts();
      renderScriptOverview();
      showToast(script.status === "已优化" ? "已标记为优化，等待下一场直播验证" : "已恢复为待优化");
    });
    $("#lowCopy").addEventListener("click", () => {
      const scripts = LOW_SCRIPTS.filter(script =>
        (state.lowAnchor === "all" || script.accountId === state.lowAnchor) &&
        (state.lowScene === "all" || script.scene === state.lowScene)
      );
      if (!scripts.length) {
        showToast("当前筛选条件下没有可复制的低效话术");
        return;
      }
      const content = scripts.map((script, index) => {
        const anchor = QUALITY_META[script.accountId];
        return `${index + 1}. ${anchor.name}｜${script.scene}\n原话：${script.quote}\n转化 ${script.conversion.toFixed(1)}%（基线 ${script.baseline.toFixed(1)}%）· 停留 ${script.dwell.toFixed(1)}s\n建议：${script.suggestion}`;
      }).join("\n\n");
      copyText(`持续低效话术优化清单（10/14–10/16）\n\n${content}`, "优化清单已复制");
    });

    $("#scriptLivePause").addEventListener("click", () => {
      if (!DIAG_LIVE[ACTIVE_ACCOUNT.id]?.live) return;
      state.scriptLivePaused = !state.scriptLivePaused;
      renderScriptLive();
    });
    $("#scriptLiveNext").addEventListener("click", () => {
      pushScriptLiveSentence();
    });

    $$("#campaignDayparts button").forEach(button => {
      button.addEventListener("click", () => {
        state.campaignDaypart = button.dataset.campaignDaypart;
        renderCampaignDecision(CAMPAIGN_DATA[ACTIVE_ACCOUNT.id] || CAMPAIGN_DATA.fashion);
      });
    });

    $("#campaignRefresh").addEventListener("click", () => {
      state.campaignSyncedAt = new Date();
      renderCampaignPage();
      showToast("已刷新实时投放数据（示例）");
    });

    $("#campaignDocUploadBtn").addEventListener("click", () => $("#campaignDocInput").click());
    $("#campaignDocInput").addEventListener("change", event => {
      handleCampaignDocFiles(event.target.files);
      event.target.value = "";
    });

    $("#campaignOperations").addEventListener("input", event => {
      const range = event.target.closest("[data-op-range]");
      if (!range) return;
      const card = range.closest("[data-operation-id]");
      const label = card?.querySelector("[data-op-value]");
      const action = CAMPAIGN_ACTIONS.find(item => item.id === card?.dataset.operationId);
      if (label) label.textContent = `${action?.direction < 0 ? "-" : "+"}${range.value}%`;
    });

    $("#campaignOperations").addEventListener("click", event => {
      const button = event.target.closest("[data-run-op]");
      if (!button) return;
      runCampaignAction(button.dataset.runOp);
    });

    $$(".review-tab").forEach(button => {
      button.addEventListener("click", () => {
        state.reviewTab = button.dataset.reviewTab;
        renderReviewPage();
      });
    });

    $$(".granularity-tabs button").forEach(button => {
      button.addEventListener("click", () => {
        state.reviewGranularity = Number(button.dataset.granularity);
        const session = getSelectedSession();
        if (session) renderReviewChart(session);
      });
    });

    $("#reviewChartWrap").addEventListener("pointermove", handleReviewChartPointer);
    $("#reviewChartWrap").addEventListener("pointerleave", hideReviewChartTooltip);

    $("#anchorVideoInput").addEventListener("change", event => {
      handleAnchorFiles(event.target.files);
      event.target.value = "";
    });

    const anchorUploadZone = $("#anchorUploadZone");
    ["dragenter", "dragover"].forEach(type => {
      anchorUploadZone.addEventListener(type, event => {
        event.preventDefault();
        anchorUploadZone.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach(type => {
      anchorUploadZone.addEventListener(type, event => {
        event.preventDefault();
        anchorUploadZone.classList.remove("dragover");
      });
    });
    anchorUploadZone.addEventListener("drop", event => {
      handleAnchorFiles(event.dataTransfer.files);
    });

    $("#anchorSwitcher").addEventListener("click", event => {
      const chip = event.target.closest("[data-host-account]");
      if (!chip) return;
      state.accountId = chip.dataset.hostAccount;
      state.scope = "account";
      renderAll();
    });

    $$("[data-open-anchor]").forEach(button => {
      button.addEventListener("click", () => {
        state.reviewTab = "anchor";
        renderReviewPage();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });

    $("[data-open-playback]").addEventListener("click", () => {
      state.reviewTab = "playback";
      renderReviewPage();
      window.setTimeout(() => {
        $(".review-chart-panel")?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 80);
    });

    $("#reviewRecordBtn").addEventListener("click", () => {
      const monitor = LIVE_MONITORS[ACTIVE_ACCOUNT.id];
      if (!monitor.live) return;
      state.recording = !state.recording;
      updateRecordStatus();
    });

    function togglePlayback() {
      const session = getSelectedSession();
      if (!session) return;
      if (state.playerTime >= session.durationSeconds) state.playerTime = 0;
      state.playerPlaying = !state.playerPlaying;
      if (state.playerPlaying) state.activeAnnotationId = null;
      renderPlayback();
    }

    $("#playerBigPlay").addEventListener("click", togglePlayback);
    $("#playerPlayBtn").addEventListener("click", togglePlayback);

    $("#playerSpeed").addEventListener("click", () => {
      const speeds = [1, 1.5, 2];
      const index = speeds.indexOf(state.playerSpeed);
      state.playerSpeed = speeds[(index + 1) % speeds.length];
      updatePlayerFrame();
    });

    $("#diagCaptureToggle").addEventListener("click", () => {
      if (!DIAG_LIVE[ACTIVE_ACCOUNT.id].live) return;
      state.diagCapturing = !state.diagCapturing;
      renderLiveDiagnosis();
    });

    $$("#diagWindowTabs button").forEach(button => {
      button.addEventListener("click", () => {
        state.diagWindow = Number(button.dataset.diagWindow);
        renderLiveDiagnosis();
      });
    });

    $("#diagBannedInput").addEventListener("change", event => {
      handleDiagBannedLibrary(event.target.files[0]);
      event.target.value = "";
    });

    $("#diagChartWrap").addEventListener("pointermove", handleDiagChartPointer);
    $("#diagChartWrap").addEventListener("pointerleave", hideDiagChartTooltip);

    $("#playerProgress").addEventListener("click", event => {
      const session = getSelectedSession();
      if (!session) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const ratio = clamp((event.clientX - rect.left) / rect.width, 0, 1);
      seekPlayback(ratio * session.durationSeconds);
    });

    $("#playerMarkers").addEventListener("click", event => {
      const marker = event.target.closest("[data-marker-id]");
      if (!marker) return;
      event.stopPropagation();
      const session = getSelectedSession();
      const annotation = session?.annotations.find(item => item.id === marker.dataset.markerId);
      if (annotation) seekPlayback(annotation.time, annotation.id);
    });

    $("#sessionList").addEventListener("click", event => {
      const item = event.target.closest("[data-session-id]");
      if (!item) return;
      state.selectedSessionId = item.dataset.sessionId;
      state.playerTime = 0;
      state.playerPlaying = false;
      state.activeAnnotationId = null;
      renderPlayback();
    });

    $("#annotationList").addEventListener("click", event => {
      const item = event.target.closest("[data-annotation-id]");
      if (!item) return;
      const session = getSelectedSession();
      const annotation = session?.annotations.find(entry => entry.id === item.dataset.annotationId);
      if (annotation) seekPlayback(annotation.time, annotation.id);
    });

    $$(".chart-tabs button").forEach(button => {
      if (!button.dataset.metric) return;
      button.addEventListener("click", () => {
        state.chartMetric = button.dataset.metric;
        $$(".chart-tabs button").forEach(tab => {
          const active = tab === button;
          tab.classList.toggle("active", active);
          tab.setAttribute("aria-selected", String(active));
        });
        renderChart(getRange(state.start, state.end), getPreviousRange(state.start, state.end));
      });
    });

    $("#applyRange").addEventListener("click", () => {
      let start = $("#startDate").value;
      let end = $("#endDate").value;
      if (!start || !end) return;
      if (start > end) [start, end] = [end, start];
      const minDate = ACTIVE_DATA[0].date;
      const maxDate = ACTIVE_DATA[ACTIVE_DATA.length - 1].date;
      state.start = clampDate(start, minDate, maxDate);
      state.end = clampDate(end, minDate, maxDate);
      if (state.start > state.end) [state.start, state.end] = [state.end, state.start];
      renderAll();
    });

    function clampDate(date, minDate, maxDate) {
      if (date < minDate) return minDate;
      if (date > maxDate) return maxDate;
      return date;
    }

    $$(".scope-switch button").forEach(button => {
      button.addEventListener("click", () => {
        state.scope = button.dataset.scope;
        renderAll();
      });
    });

    $$(".nav-item").forEach(button => {
      button.addEventListener("click", () => showView(button.dataset.viewTarget));
    });

    $$("[data-goto-view]").forEach(button => {
      button.addEventListener("click", () => showView(button.dataset.gotoView));
    });

    $("#accountTrigger").addEventListener("click", event => {
      event.stopPropagation();
      setAccountMenu($("#accountMenu").hidden);
    });

    $("#accountOptions").addEventListener("click", event => {
      const option = event.target.closest("[data-account-id]");
      if (!option) return;
      state.accountId = option.dataset.accountId;
      state.scope = "account";
      setAccountMenu(false);
      renderAll();
    });

    $("#accountList").addEventListener("click", event => {
      const row = event.target.closest("[data-account-id]");
      if (row) {
        state.accountId = row.dataset.accountId;
        state.scope = "account";
        renderAll();
        return;
      }
      if (event.target.closest("[data-action='show-total']")) {
        state.scope = "total";
        renderAll();
      }
    });

    document.addEventListener("click", event => {
      if (!event.target.closest(".account-area")) setAccountMenu(false);
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape") setAccountMenu(false);
    });

    $("#refreshBtn").addEventListener("click", () => {
      const button = $("#refreshBtn");
      button.classList.add("loading");
      window.setTimeout(() => {
        lastSyncAt = new Date();
        renderAll();
        button.classList.remove("loading");
        showToast("已按千川快照重新汇总");
      }, 260);
    });

    window.setInterval(() => {
      if (document.hidden) return;
      lastSyncAt = new Date();
      if (state.view === "data") renderAll();
      if (state.view === "material") renderMaterialPage();
    }, 30000);

    window.setInterval(() => {
      if (state.view !== "campaign" || document.hidden) return;
      state.campaignTick += 1;
      state.campaignSyncedAt = new Date();
      const data = CAMPAIGN_DATA[ACTIVE_ACCOUNT.id] || CAMPAIGN_DATA.fashion;
      const live = Boolean(DIAG_LIVE[ACTIVE_ACCOUNT.id]?.live);
      renderCampaignLiveStrip(data);
      const syncTime = state.campaignSyncedAt.toLocaleTimeString("zh-CN", { hour12: false });
      $("#campaignSyncText").innerHTML = `<i></i>${live ? "数据截止" : "演示数据截止"} ${syncTime} · 30 秒刷新`;
    }, 30000);

    window.setInterval(() => {
      if (state.view !== "diagnosis" || !state.diagCapturing) return;
      const profile = DIAG_LIVE[ACTIVE_ACCOUNT.id];
      if (!profile.live) return;
      appendDiagPoint(ACTIVE_ACCOUNT.id);
      renderLiveDiagnosis();
    }, 5000);

    window.setInterval(() => {
      if (!state.playerPlaying || state.view !== "review" || state.reviewTab !== "playback") return;
      const session = getSelectedSession();
      if (!session) return;
      state.playerTime = Math.min(session.durationSeconds, state.playerTime + state.playerSpeed);
      if (state.playerTime >= session.durationSeconds) state.playerPlaying = false;
      updatePlayerFrame();
    }, 1000);

    window.setInterval(() => {
      const monitor = LIVE_MONITORS[ACTIVE_ACCOUNT.id];
      if (!monitor.live || !state.recording || state.view !== "review") return;
      state.recordSeconds += 1;
      updateRecordStatus();
    }, 1000);

    window.setInterval(() => {
      if (state.view !== "script" || state.scriptTab !== "live") return;
      $$("[data-pending-note]").forEach(node => {
        const row = state.scriptLiveRows.find(item => item.id === node.dataset.pendingNote);
        if (!row || row.status !== "pending") return;
        const remaining = Math.max(0, Math.ceil((row.readyAt - Date.now()) / 1000));
        node.textContent = `等待 4 秒归因 · ${remaining}s`;
      });
    }, 1000);

    window.setInterval(() => {
      if (state.view !== "script" || state.scriptTab !== "live" || state.scriptLivePaused) return;
      if (!DIAG_LIVE[ACTIVE_ACCOUNT.id]?.live) return;
      pushScriptLiveSentence();
    }, 9000);

    $("#chartWrap").addEventListener("pointermove", handleChartPointer);
    $("#chartWrap").addEventListener("pointerleave", clearChartPointer);

    window.addEventListener("resize", () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => {
        if (state.view === "data") {
          renderChart(getRange(state.start, state.end), getPreviousRange(state.start, state.end));
        }
        if (state.view === "review" && state.reviewTab === "playback") {
          const session = getSelectedSession();
          if (session) renderReviewChart(session);
        }
        if (state.view === "diagnosis") {
          const profile = DIAG_LIVE[ACTIVE_ACCOUNT.id];
          if (profile) renderDiagChart(getDiagSeries(ACTIVE_ACCOUNT.id), profile);
        }
        if (state.view === "script" && state.scriptTab === "live") {
          renderScriptImpactChart();
        }
        if (state.view === "campaign") {
          renderCampaignAnomalyChart(CAMPAIGN_DATA[ACTIVE_ACCOUNT.id] || CAMPAIGN_DATA.fashion);
        }
      }, 120);
    });

    const initialParams = new URLSearchParams(window.location.search);
    const initialScriptTab = initialParams.get("scriptTab");
    if (["banned", "quality", "low", "live"].includes(initialScriptTab)) {
      state.scriptTab = initialScriptTab;
    }
    const initialDaypart = initialParams.get("daypart");
    if (["morning", "noon", "evening"].includes(initialDaypart)) {
      state.campaignDaypart = initialDaypart;
    }
    const initialAccount = initialParams.get("account");
    if (ACCOUNTS.some(account => account.id === initialAccount)) {
      state.accountId = initialAccount;
      state.scope = "account";
    }
    const initialView = (window.location.hash || "").replace("#", "");
    renderAll();
    showView(VIEW_LABELS[initialView] ? initialView : "data", false);
  
