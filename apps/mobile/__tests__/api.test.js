import { verifyNumber, createQoDSession, uploadVideo, runAI, getAIResult, api } from '../src/utils/api';
import MockAdapter from 'axios-mock-adapter';

describe('API Utils', () => {
  let mock;

  beforeAll(() => {
    mock = new MockAdapter(api);
  });

  afterEach(() => {
    mock.reset();
  });

  afterAll(() => {
    mock.restore();
  });

  it('verifyNumber should post to /nv/verify and return data', async () => {
    const mockData = { devicePhoneNumberVerified: true };
    mock.onPost('/nv/verify').reply(200, mockData);

    const result = await verifyNumber('+905390000020');
    expect(result).toEqual(mockData);
  });

  it('createQoDSession should post to /qod/session and return data', async () => {
    const mockData = { sessionId: '12345', duration: 60 };
    mock.onPost('/qod/session').reply(200, mockData);

    const result = await createQoDSession(60);
    expect(result).toEqual(mockData);
  });

  it('runAI should post to /ai-run and return data', async () => {
    const mockData = { status: 'Inference started' };
    mock.onPost('/ai-run').reply(200, mockData);

    const result = await runAI();
    expect(result).toEqual(mockData);
  });

  it('getAIResult should get from /ai-result and return data', async () => {
    const mockData = { status: 'DONE', result: {} };
    mock.onGet('/ai-result').reply(200, mockData);

    const result = await getAIResult();
    expect(result).toEqual(mockData);
  });
});
