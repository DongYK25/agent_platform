CREATE TABLE session_summaries (
    -- 数据库内部自增主键
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- 摘要记录唯一 UID
    uid UUID NOT NULL DEFAULT gen_random_uuid(),

    -- 所属用户 UID
    user_uid UUID NOT NULL,

    -- 所属会话 UID
    session_uid UUID NOT NULL,

    -- LLM 生成的自然语言摘要
    summary TEXT NOT NULL DEFAULT '',

    -- 结构化摘要，例如用户偏好、重要事实、任务等
    summary_data JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 本次摘要覆盖到的最后一条原始消息的数据库 ID
    source_last_message_id BIGINT,

    -- 本次摘要覆盖到的最后一条消息的顺序编号
    -- 后续增量查询使用：sequence_no > source_last_sequence_no
    source_last_sequence_no BIGINT NOT NULL DEFAULT 0,

    -- 本次摘要累计覆盖的原始消息数量
    source_message_count INTEGER NOT NULL DEFAULT 0,

    -- 本次摘要输入材料的Token数量
    -- 包含旧摘要和本次新增消息的内容Token
    source_token_count INTEGER,

    -- 本次生成的新摘要本身的Token数量
    summary_token_count INTEGER,

    -- 本次摘要生成时，模型API实际返回的输入Token数量
    -- 即 compression request 的 prompt_tokens
    compression_prompt_tokens INTEGER,

    -- 本次摘要生成时，模型API实际返回的输出Token数量
    -- 即 compression request 的 completion_tokens
    compression_completion_tokens INTEGER,

    -- 本次压缩所使用的大模型名称
    compression_model VARCHAR(100),

    -- 摘要压缩使用的Prompt版本，方便后续追踪
    prompt_version VARCHAR(50),

    -- 摘要版本，每次成功更新递增
    version INTEGER NOT NULL DEFAULT 1,

    -- 摘要首次创建时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 摘要最后更新时间，每次更新时由业务代码维护
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 摘要 UID 必须唯一
    CONSTRAINT uk_session_summaries_uid
        UNIQUE (uid),

    -- 一个用户的一个 Session 只保存一份最新摘要
    CONSTRAINT uk_session_summaries_session
        UNIQUE (user_uid, session_uid),

    -- 最后一条已压缩消息必须属于同一个用户、同一个Session
    CONSTRAINT fk_summary_source_message
        FOREIGN KEY (user_uid, session_uid, source_last_message_id)
        REFERENCES session_messages (user_uid, session_uid, id)
        ON DELETE RESTRICT,

    -- 摘要版本必须大于等于1
    CONSTRAINT ck_summary_version
        CHECK (version >= 1),

    -- 消息顺序边界不能为负数
    CONSTRAINT ck_summary_last_sequence
        CHECK (source_last_sequence_no >= 0),

    -- 消息数量不能为负数
    CONSTRAINT ck_summary_message_count
        CHECK (source_message_count >= 0),

    -- Token 数量不能为负数
    CONSTRAINT ck_summary_token_count
        CHECK (
            (source_token_count IS NULL OR source_token_count >= 0)
            AND
            (summary_token_count IS NULL OR summary_token_count >= 0)
            AND
            (compression_prompt_tokens IS NULL OR compression_prompt_tokens >= 0)
            AND
            (compression_completion_tokens IS NULL OR compression_completion_tokens >= 0)
        )
);

-- 表说明
COMMENT ON TABLE session_summaries IS
'会话摘要表，保存每个Session最新的LLM压缩摘要，用于后续对话的历史记忆加载。';

-- 字段说明
COMMENT ON COLUMN session_summaries.id IS
'数据库内部自增主键。';

COMMENT ON COLUMN session_summaries.uid IS
'摘要记录唯一UID。';

COMMENT ON COLUMN session_summaries.user_uid IS
'所属用户UID。';

COMMENT ON COLUMN session_summaries.session_uid IS
'所属会话UID，与原始消息表中的session_uid对应。';

COMMENT ON COLUMN session_summaries.summary IS
'LLM生成的自然语言摘要，通常包含本次会话的核心信息和上下文。';

COMMENT ON COLUMN session_summaries.summary_data IS
'结构化摘要数据，以JSONB形式保存用户偏好、重要事实、待办事项等信息。';

COMMENT ON COLUMN session_summaries.source_last_message_id IS
'本次摘要覆盖的最后一条原始消息的数据库自增ID，用于定位原始消息。';

COMMENT ON COLUMN session_summaries.source_last_sequence_no IS
'本次摘要覆盖的最后一条消息的顺序编号，用于增量压缩时确定消息查询起点。';

COMMENT ON COLUMN session_summaries.source_message_count IS
'本次摘要累计覆盖的原始消息数量。';

COMMENT ON COLUMN session_summaries.source_token_count IS
'本次摘要压缩输入材料的Token数量，包含旧摘要与新增消息，不代表API实际消耗。';

COMMENT ON COLUMN session_summaries.summary_token_count IS
'本次生成的新摘要自身的Token数量，不代表API实际消耗。';

COMMENT ON COLUMN session_summaries.compression_prompt_tokens IS
'模型API实际返回的本次摘要压缩请求输入Token数量。';

COMMENT ON COLUMN session_summaries.compression_completion_tokens IS
'模型API实际返回的本次摘要压缩请求输出Token数量。';

COMMENT ON COLUMN session_summaries.compression_model IS
'生成本次摘要所使用的大模型名称。';

COMMENT ON COLUMN session_summaries.prompt_version IS
'摘要压缩Prompt版本，便于后续调整和追踪压缩效果。';

COMMENT ON COLUMN session_summaries.version IS
'摘要版本号，每次成功更新摘要递增。';

COMMENT ON COLUMN session_summaries.created_at IS
'摘要首次创建时间。';

COMMENT ON COLUMN session_summaries.updated_at IS
'摘要最后更新时间，需要在业务更新时主动维护。';


-- 按用户查询最近更新的摘要
CREATE INDEX idx_session_summaries_user_updated
ON session_summaries (user_uid, updated_at DESC);