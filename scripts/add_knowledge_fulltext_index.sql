-- Add keyword-search FULLTEXT index for existing FinRegQA MySQL databases.
-- MySQL's ngram parser supports CJK keyword search without an external service.

ALTER TABLE `knowledge`
ADD FULLTEXT INDEX `idx_knowledge_fulltext` (
    `content`,
    `category`,
    `regulation_type`,
    `article_number`,
    `section_number`
) WITH PARSER ngram;
