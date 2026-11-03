CREATE TABLE session_messages (
    -- 数据库内部自增主键
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- 消息唯一 UID，对外使用，不依赖数据库自增 ID
    uid UUID NOT NULL DEFAULT gen_random_uuid(),

    -- 所属用户 UID
    user_uid UUID NOT NULL,

    -- 所属会话 UID，同一个对话窗口内保持一致
    session_uid UUID NOT NULL,

    -- 当前消息在 Session 中的顺序，从 1 开始递增
    sequence_no BIGINT NOT NULL,

    -- 消息角色：user / assistant / system / developer / tool
    role VARCHAR(20) NOT NULL,

    -- 消息原始内容，保留完整内容，不进行摘要覆盖
    content TEXT NOT NULL,

    -- 内容类型，例如 text / image / multimodal
    content_type VARCHAR(30) NOT NULL DEFAULT 'text',

    -- 当前消息内容本身的 Token 数量
    -- 注意：不是整个大模型请求的实际 Token 消耗
    content_token_count INTEGER,

    -- Token 计算方式：tokenizer（Tokenizer 计算）/ estimated（估算）
    token_count_method VARCHAR(20),

    -- 计算 Token 时所使用的模型或 Tokenizer 标识
    -- 不同模型的 Tokenizer 可能不同
    tokenizer_model VARCHAR(100),

    -- 扩展元数据，例如 tool_call_id、工具名称、工具调用参数等
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- 消息创建时间
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 每条消息的 UID 必须唯一
    CONSTRAINT uk_session_messages_uid
        UNIQUE (uid),

    -- 同一个用户、同一个 Session 下，消息顺序不能重复
    CONSTRAINT uk_session_sequence
        UNIQUE (user_uid, session_uid, sequence_no),

    -- 为摘要表提供同用户、同会话的消息引用约束
    CONSTRAINT uk_session_message_ref
        UNIQUE (user_uid, session_uid, id),

    -- 限制消息角色
    CONSTRAINT ck_session_message_role
        CHECK (
            role IN ('user', 'assistant', 'system', 'developer', 'tool')
        ),

    -- Token 数量不能为负数
    CONSTRAINT ck_session_message_token_count
        CHECK (
            content_token_count IS NULL
            OR content_token_count >= 0
        ),

    -- 限制 Token 计算方式
    CONSTRAINT ck_session_message_token_method
        CHECK (
            token_count_method IS NULL
            OR token_count_method IN ('tokenizer', 'estimated')
        )
);

-- 表说明
COMMENT ON TABLE session_messages IS
'原始对话消息表，保存用户、AI、工具等产生的完整消息，采用只追加的方式保存历史记录。';

-- 字段说明
COMMENT ON COLUMN session_messages.id IS
'数据库内部自增主键。';

COMMENT ON COLUMN session_messages.uid IS
'消息唯一UID，用于对外标识消息。';

COMMENT ON COLUMN session_messages.user_uid IS
'所属用户UID。';

COMMENT ON COLUMN session_messages.session_uid IS
'所属会话UID，一个独立的聊天会话使用一个UID。';

COMMENT ON COLUMN session_messages.sequence_no IS
'消息在当前Session中的顺序编号，从1开始递增。';

COMMENT ON COLUMN session_messages.role IS
'消息角色，区分用户、AI、系统、开发者和工具消息。';

COMMENT ON COLUMN session_messages.content IS
'消息原始内容，完整保存，不直接修改历史数据。';

COMMENT ON COLUMN session_messages.content_type IS
'消息内容类型，例如文本、图片、多模态内容。';

COMMENT ON COLUMN session_messages.content_token_count IS
'消息内容本身的Token数量，用于上下文长度统计，不代表实际API消耗。';

COMMENT ON COLUMN session_messages.token_count_method IS
'Token计算方式，tokenizer表示使用对应Tokenizer计算，estimated表示估算。';

COMMENT ON COLUMN session_messages.tokenizer_model IS
'Token计算所依据的模型或Tokenizer标识。';

COMMENT ON COLUMN session_messages.metadata IS
'扩展元数据，保存工具调用信息、工具名称、调用参数等结构化内容。';

COMMENT ON COLUMN session_messages.created_at IS
'消息创建时间。';


-- 按用户查询历史消息及创建时间
CREATE INDEX idx_session_messages_user_created
ON session_messages (user_uid, created_at DESC);